#!/usr/bin/env python3
"""
完整视频生成流程测试
从视频分析、剪辑决策、脚本生成、TTS、到最终视频生成
"""
import os
import sys
import asyncio
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.adapters.vision_adapters import DashScopeVisionAdapter
from app.adapters.audio_adapters import ParaformerSpeechAdapter
from app.prompts.llm_prompts import VideoAnalysisPrompts, ClipDecisionPrompts
from app.utils.video_utils import video_to_base64, get_video_info
from app.utils.audio_utils import extract_audio_from_video
from app.utils.oss_client import oss_client
from app.services.video_compression import video_compression_service
from app.utils.ai_clients.dashscope_client import DashScopeClient
from app.services.video_production_orchestrator import video_production_orchestrator


def print_section(title: str):
    """打印章节标题"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def clean_json_response(response: str) -> str:
    """清理LLM返回的JSON（移除markdown代码块标记）"""
    response = response.strip()
    if response.startswith("```json"):
        response = response[7:]
    elif response.startswith("```"):
        response = response[3:]
    if response.endswith("```"):
        response = response[:-3]
    return response.strip()


async def test_full_production():
    """测试完整视频生成流程"""
    print_section("完整视频生成流程测试 - 从分析到成品视频")

    test_video = "tmp/7514135682735639860.mp4"
    compressed_video = "tmp/test_compressed_production.mp4"
    audio_path = "tmp/test_audio_production.mp3"
    audio_oss_path = "test/test_audio_production.mp3"

    # 最终输出视频
    final_video = f"tmp/final_video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"

    try:
        if not os.path.exists(test_video):
            print(f"❌ 测试视频不存在: {test_video}")
            return False

        print(f"\n📹 测试视频: {test_video}")
        video_info = get_video_info(test_video)
        print(f"   时长: {video_info['duration']:.2f}秒")
        print(f"   分辨率: {video_info['width']}x{video_info['height']}")
        print(f"   大小: {video_info['size_bytes'] / 1024 / 1024:.2f} MB")

        # ==================== 阶段 A: 视频分析和剪辑决策 ====================
        print_section("阶段 A: 视频分析和剪辑决策 (复用之前的流程)")

        # A1. 压缩视频
        print("\n🗜️  压缩视频...")
        compressed_path, stats = await video_compression_service.compress_video(
            input_path=test_video,
            output_path=compressed_video,
            profile_name="aggressive"
        )
        print(f"✅ 压缩完成: {stats['original_size'] / 1024 / 1024:.2f} MB → "
              f"{stats['compressed_size'] / 1024 / 1024:.2f} MB")

        # A2. 视觉分析
        print("\n🤖 调用 VL 模型获取视觉分析...")
        video_base64 = video_to_base64(compressed_path)
        vision_adapter = DashScopeVisionAdapter()

        visual_result = await vision_adapter.analyze_from_base64(
            video_base64=video_base64,
            prompt=VideoAnalysisPrompts.VISUAL_ANALYSIS_JSON
        )

        visual_json_text = clean_json_response(visual_result)
        visual_json = json.loads(visual_json_text)
        print(f"✅ VL 分析完成: {len(visual_json.get('segments', []))} 个时间分段")

        # A3. 语音识别
        print("\n🎵 提取音频并进行ASR识别...")
        extract_audio_from_video(test_video, audio_path)
        await oss_client.upload(local_path=audio_path, oss_path=audio_oss_path)
        audio_url = oss_client.generate_signed_url(audio_oss_path, expires=86400)

        speech_adapter = ParaformerSpeechAdapter()
        asr_transcription = await speech_adapter.transcribe_from_url(
            audio_url=audio_url,
            language_hints=["zh", "en"]
        )
        print(f"✅ ASR 识别完成: {len(asr_transcription.get('sentences', []))} 句话")

        # A4. 生成剪辑决策
        print("\n📝 生成剪辑决策...")
        video_analyses = [
            {
                'video_id': 'video_001',
                'duration': video_info['duration'],
                'visual_analysis_json': visual_json,
                'asr_transcription': asr_transcription
            }
        ]

        enhanced_prompt = ClipDecisionPrompts.generate_enhanced_clip_decision_prompt(
            theme="运动鞋产品展示精彩片段",
            video_analyses=video_analyses,
            target_duration=10
        )

        llm_client = DashScopeClient()
        clip_decision_response = await llm_client.chat(
            prompt=enhanced_prompt,
            system_prompt=ClipDecisionPrompts.CLIP_DECISION_SYSTEM
        )

        clip_decision_text = clean_json_response(clip_decision_response)
        clip_decision = json.loads(clip_decision_text)

        print(f"✅ 剪辑决策生成完成:")
        print(f"   - 主题: {clip_decision.get('theme', '')}")
        print(f"   - 片段数: {len(clip_decision.get('clips', []))}")
        print(f"   - 目标时长: {clip_decision.get('total_duration', 0)}秒")

        # 保存剪辑决策
        decision_file = "tmp/clip_decision_for_production.json"
        with open(decision_file, 'w', encoding='utf-8') as f:
            json.dump(clip_decision, f, ensure_ascii=False, indent=2)
        print(f"💾 剪辑决策已保存: {decision_file}")

        # ==================== 阶段 B: 完整视频生成流程 ====================
        print_section("阶段 B: 完整视频生成流程 (新流程)")

        print("\n🎬 开始调用 VideoProductionOrchestrator...")
        print(f"   配音风格: professional")
        print(f"   TTS音色: Cherry (女声)")
        print(f"   是否添加配音: True")
        print(f"   原音音量: 0.2 (降低原音，突出配音)")

        # 调用编排服务生成最终视频
        production_result = await video_production_orchestrator.produce_video_from_decision(
            source_videos=[test_video],
            clip_decision=clip_decision,
            output_path=final_video,
            narration_style="professional",
            narration_voice="Cherry",  # 使用qwen3-tts-flash支持的Cherry音色
            add_narration=True,
            background_music_path=None,  # 暂不添加背景音乐
            original_audio_volume=0.2  # 降低原音，让配音更清晰
        )

        # ==================== 测试结果总结 ====================
        print_section("测试结果总结")

        print("\n✅ 完整视频生成流程测试通过!")

        print(f"\n📊 流程统计:")
        print(f"   【阶段A - 视频分析】")
        print(f"   - 原始视频: {video_info['size_bytes'] / 1024 / 1024:.2f} MB")
        print(f"   - 压缩后: {stats['compressed_size'] / 1024 / 1024:.2f} MB")
        print(f"   - 视觉分段: {len(visual_json.get('segments', []))} 个")
        print(f"   - 语音句子: {len(asr_transcription.get('sentences', []))} 句")
        print(f"   - 剪辑片段: {len(clip_decision.get('clips', []))} 个")

        print(f"\n   【阶段B - 视频生成】")
        stats = production_result['statistics']
        print(f"   - 最终视频时长: {stats['final_duration']:.2f}秒")
        print(f"   - 最终文件大小: {stats['final_size_mb']:.2f}MB")
        print(f"   - 总处理时间: {stats['processing_time']:.2f}秒")
        print(f"   - 配音状态: {'已添加' if stats['has_narration'] else '未添加'}")
        if stats.get('script_word_count'):
            print(f"   - 脚本字数: {stats['script_word_count']}字")
            print(f"   - 预估朗读时长: {stats['script_estimated_duration']:.1f}秒")

        print(f"\n📁 输出文件:")
        print(f"   - 剪辑决策: {decision_file}")
        print(f"   - 最终视频: {production_result['final_video_path']}")
        print(f"   - 中间文件数量: {len(production_result['intermediate_files'])}")

        # 可选: 显示中间文件列表
        print(f"\n📂 中间文件列表:")
        for i, file_path in enumerate(production_result['intermediate_files'], 1):
            file_size = os.path.getsize(file_path) / 1024
            print(f"   {i}. {Path(file_path).name} ({file_size:.2f}KB)")

        # ==================== 清理临时文件 ====================
        print_section("清理临时文件")

        print("\n🗑️  清理临时文件...")
        if os.path.exists(compressed_video):
            os.remove(compressed_video)
            print(f"✅ 删除: {compressed_video}")
        if os.path.exists(audio_path):
            os.remove(audio_path)
            print(f"✅ 删除: {audio_path}")
        await oss_client.delete(audio_oss_path)
        print(f"✅ 删除: OSS/{audio_oss_path}")

        # 注意: 保留最终视频和中间文件用于检查
        print(f"\n💡 提示: 最终视频和中间文件已保留，可手动查看验证")

        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

        # 清理可能残留的文件
        try:
            if os.path.exists(compressed_video):
                os.remove(compressed_video)
            if os.path.exists(audio_path):
                os.remove(audio_path)
            if oss_client.object_exists(audio_oss_path):
                await oss_client.delete(audio_oss_path)
        except:
            pass

        return False


async def main():
    """主函数"""
    print("\n" + "🎬" * 40)
    print("  完整视频生成流程测试")
    print("  视频分析 → 剪辑决策 → 脚本生成 → TTS → 最终视频")
    print("🎬" * 40)

    success = await test_full_production()

    if success:
        print("\n🎉 所有测试通过！完整视频生成系统工作正常！")
    else:
        print("\n⚠️  测试失败，请检查错误信息")

    print("\n" + "🎬" * 40)


if __name__ == "__main__":
    asyncio.run(main())
