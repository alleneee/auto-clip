#!/usr/bin/env python3
"""
完整视频生产流程演示
展示如何使用完整的批处理+生产一体化工作流

功能：
1. 多视频输入 → AI分析
2. 智能剪辑计划生成
3. 视频片段提取和拼接
4. 基于内容自动生成脚本
5. TTS语音合成
6. 音视频合成
7. 质量评分

使用场景：
- 自媒体创作：多个素材一键成片
- 教育视频：课程素材自动生成讲解
- 新闻快讯：片段自动生成解说
- Vlog制作：旅行素材自动故事化
"""

import asyncio
import httpx
import json
import time
from pathlib import Path
from typing import Dict, Any, List


class CompleteVideoProductionDemo:
    """完整视频生产演示客户端"""

    def __init__(self, api_base: str = "http://localhost:8000"):
        self.api_base = api_base
        self.client = httpx.AsyncClient(timeout=600.0)

    async def start_production(
        self,
        video_paths: List[str],
        config: Dict[str, Any]
    ) -> str:
        """
        启动完整视频生产流程

        Args:
            video_paths: 源视频文件路径列表
            config: 生产配置
                - add_narration: 是否添加口播（必须为True以启用完整流程）
                - narration_voice: TTS语音类型
                - background_music_path: 背景音乐路径（可选）
                - background_music_volume: 背景音乐音量
                - target_duration: 目标时长
                - min_clip_duration: 最小片段时长
                - transition_type: 转场类型

        Returns:
            任务ID
        """
        url = f"{self.api_base}/api/v1/batch/process"

        payload = {
            "video_paths": video_paths,
            "config": config
        }

        print("📤 发起完整视频生产请求...")
        print(f"   视频数量: {len(video_paths)}")
        print(f"   配置: {json.dumps(config, ensure_ascii=False, indent=2)}")

        response = await self.client.post(url, json=payload)
        response.raise_for_status()

        result = response.json()
        task_id = result.get("task_id")

        print(f"✅ 任务已创建: {task_id}")
        return task_id

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        url = f"{self.api_base}/api/v1/tasks/{task_id}/status"
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()

    async def wait_for_completion(
        self,
        task_id: str,
        check_interval: int = 10
    ) -> Dict[str, Any]:
        """
        等待任务完成并显示进度

        Args:
            task_id: 任务ID
            check_interval: 检查间隔（秒）

        Returns:
            最终结果
        """
        print(f"\n⏳ 等待任务完成 (任务ID: {task_id})...")

        stage_emojis = {
            "preparing": "📦",
            "compressing": "🗜️",
            "analyzing": "🔍",
            "planning": "📋",
            "clipping": "✂️",
            "producing": "🎬",
            "completed": "✅",
            "failed": "❌"
        }

        last_stage = None
        start_time = time.time()

        while True:
            status = await self.get_task_status(task_id)
            current_stage = status.get("stage", "unknown")
            progress = status.get("progress", 0)

            # 显示阶段变化
            if current_stage != last_stage:
                emoji = stage_emojis.get(current_stage, "🔄")
                elapsed = time.time() - start_time
                print(f"\n{emoji} 阶段: {current_stage.upper()} (已用时: {elapsed:.1f}s)")
                last_stage = current_stage

            # 显示进度
            print(f"   进度: {progress:.1f}%", end="\r")

            # 检查是否完成
            if status.get("status") == "completed":
                elapsed = time.time() - start_time
                print(f"\n✅ 任务完成! 总耗时: {elapsed:.1f}s")
                return status

            # 检查是否失败
            if status.get("status") == "failed":
                error = status.get("error", "未知错误")
                print(f"\n❌ 任务失败: {error}")
                return status

            await asyncio.sleep(check_interval)

    def display_results(self, result: Dict[str, Any]):
        """
        显示完整的生产结果

        包括：
        - 最终视频信息
        - 生成的脚本
        - 质量评分
        - 统计信息
        """
        print("\n" + "="*60)
        print("📊 完整视频生产结果")
        print("="*60)

        # 最终视频
        if "final_video" in result:
            video = result["final_video"]
            print("\n🎬 最终视频:")
            print(f"   URL: {video.get('url', 'N/A')}")
            print(f"   本地路径: {video.get('path', 'N/A')}")
            print(f"   时长: {video.get('duration', 0):.1f}秒")

        # 生成的脚本
        if "script" in result:
            script = result["script"]
            print("\n📝 生成的视频脚本:")
            print(f"   完整文本: {script.get('full_text', 'N/A')[:100]}...")
            if "segments" in script:
                print(f"   段落数: {len(script['segments'])}")

        # 质量评分
        if "quality_scores" in result:
            scores = result["quality_scores"]
            print("\n⭐ 质量评分 (5维度):")
            print(f"   叙事连贯性: {scores.get('narrative_coherence', 0):.2f}")
            print(f"   音画同步: {scores.get('audio_video_sync', 0):.2f}")
            print(f"   内容覆盖: {scores.get('content_coverage', 0):.2f}")
            print(f"   制作质量: {scores.get('production_quality', 0):.2f}")
            print(f"   吸引力: {scores.get('engagement_potential', 0):.2f}")
            print(f"   ━━━━━━━━━━━━━━━━━━━━")
            print(f"   综合评分: {scores.get('overall_score', 0):.2f}")

        # 统计信息
        if "statistics" in result:
            stats = result["statistics"]
            print("\n📈 统计信息:")
            print(f"   源视频数: {stats.get('source_videos', 0)}")
            print(f"   视频片段数: {stats.get('total_clips', 0)}")
            print(f"   总时长: {stats.get('total_duration', 0):.1f}秒")
            print(f"   口播时长: {stats.get('narration_duration', 0):.1f}秒")
            print(f"   处理耗时: {stats.get('processing_time', 0):.1f}秒")

        print("\n" + "="*60)

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()


async def demo_basic_narration():
    """
    演示1: 基础口播视频生成
    最简单的完整流程配置
    """
    print("\n" + "="*60)
    print("🎯 演示1: 基础口播视频生成")
    print("="*60)

    demo = CompleteVideoProductionDemo()

    try:
        # 配置
        video_paths = [
            "/path/to/your/video1.mp4",
            "/path/to/your/video2.mp4"
        ]

        config = {
            "add_narration": True,  # 启用完整流程的关键配置
            "narration_voice": "longxiaochun",  # 龙小春语音
            "target_duration": 60,
            "min_clip_duration": 2.0
        }

        # 启动
        task_id = await demo.start_production(video_paths, config)

        # 等待完成
        result = await demo.wait_for_completion(task_id)

        # 显示结果
        demo.display_results(result)

    finally:
        await demo.close()


async def demo_with_background_music():
    """
    演示2: 带背景音乐的完整视频
    添加背景音乐混合
    """
    print("\n" + "="*60)
    print("🎯 演示2: 带背景音乐的完整视频")
    print("="*60)

    demo = CompleteVideoProductionDemo()

    try:
        video_paths = [
            "/path/to/your/video1.mp4",
            "/path/to/your/video2.mp4"
        ]

        config = {
            "add_narration": True,
            "narration_voice": "longxiaochun",
            "background_music_path": "/path/to/background_music.mp3",
            "background_music_volume": 0.2,  # 背景音乐音量20%
            "target_duration": 90,
            "min_clip_duration": 3.0,
            "transition_type": "crossfade"  # 交叉淡化转场
        }

        task_id = await demo.start_production(video_paths, config)
        result = await demo.wait_for_completion(task_id)
        demo.display_results(result)

    finally:
        await demo.close()


async def demo_educational_video():
    """
    演示3: 教育视频生成
    适用于课程、教程等场景
    """
    print("\n" + "="*60)
    print("🎯 演示3: 教育视频自动生成")
    print("="*60)

    demo = CompleteVideoProductionDemo()

    try:
        video_paths = [
            "/path/to/lesson/intro.mp4",
            "/path/to/lesson/content1.mp4",
            "/path/to/lesson/content2.mp4",
            "/path/to/lesson/summary.mp4"
        ]

        config = {
            "add_narration": True,
            "narration_voice": "zhimi",  # 知米语音（更正式）
            "target_duration": 300,  # 5分钟教学视频
            "min_clip_duration": 5.0,
            "transition_type": "fade",
            "background_music_path": "/path/to/calm_music.mp3",
            "background_music_volume": 0.15
        }

        task_id = await demo.start_production(video_paths, config)
        result = await demo.wait_for_completion(task_id)
        demo.display_results(result)

    finally:
        await demo.close()


async def demo_vlog_production():
    """
    演示4: Vlog自动制作
    旅行/生活素材自动生成故事化视频
    """
    print("\n" + "="*60)
    print("🎯 演示4: Vlog自动制作")
    print("="*60)

    demo = CompleteVideoProductionDemo()

    try:
        video_paths = [
            "/path/to/vlog/morning.mp4",
            "/path/to/vlog/sightseeing.mp4",
            "/path/to/vlog/food.mp4",
            "/path/to/vlog/sunset.mp4",
            "/path/to/vlog/night.mp4"
        ]

        config = {
            "add_narration": True,
            "narration_voice": "longxiaochun",  # 亲切的语音
            "target_duration": 180,  # 3分钟Vlog
            "min_clip_duration": 4.0,
            "transition_type": "crossfade",
            "background_music_path": "/path/to/upbeat_music.mp3",
            "background_music_volume": 0.25
        }

        task_id = await demo.start_production(video_paths, config)
        result = await demo.wait_for_completion(task_id)
        demo.display_results(result)

    finally:
        await demo.close()


async def demo_comparison_workflows():
    """
    演示5: 工作流对比
    展示基础流程 vs 完整流程的区别
    """
    print("\n" + "="*60)
    print("🎯 演示5: 工作流对比")
    print("="*60)

    demo = CompleteVideoProductionDemo()

    try:
        video_paths = [
            "/path/to/video1.mp4",
            "/path/to/video2.mp4"
        ]

        # 基础流程（不添加口播）
        print("\n📌 方式A: 基础剪辑流程")
        print("   仅视频分析 + 剪辑 + 拼接")
        config_basic = {
            "add_narration": False,  # 不启用口播
            "target_duration": 60,
            "transition_type": "fade"
        }

        task_id_basic = await demo.start_production(video_paths, config_basic)
        result_basic = await demo.wait_for_completion(task_id_basic)

        print("\n✅ 基础流程完成:")
        print(f"   输出: 拼接视频")
        print(f"   耗时: {result_basic.get('statistics', {}).get('processing_time', 0):.1f}秒")

        # 完整流程（添加口播）
        print("\n📌 方式B: 完整生产流程")
        print("   视频分析 + 剪辑 + 脚本生成 + TTS + 音视频合成")
        config_full = {
            "add_narration": True,  # 启用完整流程
            "narration_voice": "longxiaochun",
            "target_duration": 60,
            "transition_type": "fade",
            "background_music_path": "/path/to/music.mp3",
            "background_music_volume": 0.2
        }

        task_id_full = await demo.start_production(video_paths, config_full)
        result_full = await demo.wait_for_completion(task_id_full)

        print("\n✅ 完整流程完成:")
        print(f"   输出: 带口播的完整视频")
        print(f"   耗时: {result_full.get('statistics', {}).get('processing_time', 0):.1f}秒")
        print(f"   质量评分: {result_full.get('quality_scores', {}).get('overall_score', 0):.2f}")

        # 对比总结
        print("\n" + "="*60)
        print("📊 流程对比总结:")
        print("="*60)
        print(f"基础流程耗时: {result_basic.get('statistics', {}).get('processing_time', 0):.1f}秒")
        print(f"完整流程耗时: {result_full.get('statistics', {}).get('processing_time', 0):.1f}秒")
        print(f"\n完整流程额外时间: 用于脚本生成、TTS合成、音视频混合")
        print(f"完整流程产出: 更丰富的内容、更好的用户体验、更高的质量")

    finally:
        await demo.close()


def print_menu():
    """显示演示菜单"""
    print("\n" + "="*60)
    print("🎬 Auto-Clip 完整视频生产流程演示")
    print("="*60)
    print("\n选择演示:")
    print("1. 基础口播视频生成（最简单）")
    print("2. 带背景音乐的完整视频")
    print("3. 教育视频自动生成")
    print("4. Vlog自动制作")
    print("5. 工作流对比（基础 vs 完整）")
    print("0. 退出")
    print("\n提示: 请先确保API服务正在运行 (http://localhost:8000)")
    print("      并且已配置好 DASHSCOPE_API_KEY")


async def main():
    """主函数"""
    demos = {
        "1": demo_basic_narration,
        "2": demo_with_background_music,
        "3": demo_educational_video,
        "4": demo_vlog_production,
        "5": demo_comparison_workflows
    }

    while True:
        print_menu()
        choice = input("\n请选择 (0-5): ").strip()

        if choice == "0":
            print("\n👋 再见!")
            break

        if choice in demos:
            try:
                await demos[choice]()
            except Exception as e:
                print(f"\n❌ 演示出错: {e}")
                import traceback
                traceback.print_exc()

            input("\n按回车继续...")
        else:
            print("\n❌ 无效选择，请重试")


if __name__ == "__main__":
    asyncio.run(main())
