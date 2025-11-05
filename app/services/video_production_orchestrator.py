"""
视频生成编排服务 - 协调完整的视频生成流程
职责: 编排从剪辑决策到最终视频的完整流程
"""
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from app.services.video_editing import video_editing_service
from app.services.script_generation import script_generation_service
from app.adapters.tts_adapters import DashScopeTTSAdapter
from app.services.video_audio_composer import video_audio_composer
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class VideoProductionOrchestrator:
    """
    视频生成编排服务

    完整流程:
    1. 根据剪辑决策裁剪视频片段
    2. 拼接视频片段
    3. 基于剪辑内容生成解说脚本
    4. 将脚本转换为TTS音频
    5. 合成视频与TTS音频
    6. (可选)添加背景音乐
    """

    def __init__(self):
        """初始化编排服务"""
        self.video_editing = video_editing_service
        self.script_generator = script_generation_service
        self.tts_adapter = DashScopeTTSAdapter()
        self.audio_composer = video_audio_composer

    async def produce_video_from_decision(
        self,
        source_videos: List[str],
        clip_decision: Dict[str, Any],
        output_path: str,
        narration_style: str = "professional",
        narration_voice: str = "Cherry",  # qwen3-tts-flash默认音色
        add_narration: bool = True,
        background_music_path: Optional[str] = None,
        original_audio_volume: float = 0.3
    ) -> Dict[str, Any]:
        """
        根据剪辑决策生成最终视频

        Args:
            source_videos: 源视频路径列表
            clip_decision: 剪辑决策JSON，包含:
                - theme: 主题
                - total_duration: 总时长
                - clips: 剪辑片段列表
            output_path: 最终输出路径
            narration_style: 解说风格 (professional/casual/enthusiastic/educational)
            narration_voice: TTS音色 (Cherry/Peach/Plum等qwen3-tts-flash支持的音色)
            add_narration: 是否添加配音解说
            background_music_path: 背景音乐路径（可选）
            original_audio_volume: 原视频音量（0.0-1.0）

        Returns:
            Dict包含:
                - final_video_path: 最终视频路径
                - intermediate_files: 中间文件路径
                - statistics: 统计信息
                - processing_time: 总处理时间

        Raises:
            ValueError: 输入参数无效或处理失败
        """
        start_time = datetime.now()
        intermediate_files = []

        try:
            logger.info(
                f"开始视频生成流程:\n"
                f"  主题: {clip_decision.get('theme', 'Unknown')}\n"
                f"  源视频数: {len(source_videos)}\n"
                f"  剪辑片段数: {len(clip_decision.get('clips', []))}\n"
                f"  目标时长: {clip_decision.get('total_duration', 0)}秒\n"
                f"  是否添加配音: {add_narration}\n"
                f"  解说风格: {narration_style if add_narration else 'N/A'}"
            )

            # ========== 步骤1: 裁剪视频片段 ==========
            logger.info("[步骤 1/6] 开始裁剪视频片段...")
            clip_paths = await self._extract_clips(source_videos, clip_decision)
            intermediate_files.extend(clip_paths)
            logger.info(f"✅ 裁剪完成，生成 {len(clip_paths)} 个片段")

            # ========== 步骤2: 拼接视频片段 ==========
            logger.info("[步骤 2/6] 开始拼接视频片段...")
            concatenated_video = os.path.join(
                settings.temp_dir,
                f"concatenated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            )
            concat_result, concat_stats = await self.video_editing.concatenate_clips(
                clip_paths=clip_paths,
                output_path=concatenated_video,
                output_quality='high',
                add_transitions=False
            )
            intermediate_files.append(concatenated_video)
            logger.info(f"✅ 拼接完成: {concat_stats['total_duration']:.2f}秒")

            # ========== 步骤3: 生成解说脚本 (可选) ==========
            script_data = None
            if add_narration:
                logger.info("[步骤 3/6] 开始生成解说脚本...")
                script_data = await self.script_generator.generate_narration_script(
                    theme=clip_decision.get('theme', '精彩视频'),
                    clips=clip_decision.get('clips', []),
                    target_duration=concat_stats['total_duration'],
                    style=narration_style
                )
                logger.info(
                    f"✅ 脚本生成完成: {script_data['word_count']}字, "
                    f"预估时长 {script_data['estimated_duration']:.1f}秒"
                )
            else:
                logger.info("[步骤 3/6] 跳过解说脚本生成")

            # ========== 步骤4: 生成TTS音频 (可选) ==========
            tts_audio_path = None
            if add_narration and script_data:
                logger.info("[步骤 4/6] 开始生成TTS音频...")
                tts_audio_path = os.path.join(
                    settings.temp_dir,
                    f"narration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
                )

                # 调用TTS服务
                audio_data = await self.tts_adapter.synthesize_speech(
                    text=script_data['full_script'],
                    voice=narration_voice,
                    output_format='mp3'
                )

                # 保存音频文件
                with open(tts_audio_path, 'wb') as f:
                    f.write(audio_data)

                intermediate_files.append(tts_audio_path)
                audio_size_kb = len(audio_data) / 1024
                logger.info(f"✅ TTS音频生成完成: {audio_size_kb:.2f}KB")
            else:
                logger.info("[步骤 4/6] 跳过TTS音频生成")

            # ========== 步骤5: 合成视频与TTS音频 (可选) ==========
            video_with_narration = concatenated_video
            if add_narration and tts_audio_path:
                logger.info("[步骤 5/6] 开始合成视频与配音...")
                video_with_narration = os.path.join(
                    settings.temp_dir,
                    f"with_narration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
                )

                compose_stats = await self.audio_composer.compose_with_narration(
                    video_path=concatenated_video,
                    audio_path=tts_audio_path,
                    output_path=video_with_narration,
                    audio_volume=1.0,  # 配音音量
                    original_audio_volume=original_audio_volume,  # 原音音量
                    fade_duration=0.5
                )

                intermediate_files.append(video_with_narration)
                logger.info(f"✅ 视频配音合成完成: {compose_stats['output_size_mb']:.2f}MB")
            else:
                logger.info("[步骤 5/6] 跳过视频配音合成")

            # ========== 步骤6: 添加背景音乐 (可选) ==========
            if background_music_path and os.path.exists(background_music_path):
                logger.info("[步骤 6/6] 开始添加背景音乐...")
                final_video = output_path

                music_stats = await self.audio_composer.add_background_music(
                    video_path=video_with_narration,
                    music_path=background_music_path,
                    output_path=final_video,
                    music_volume=0.15,  # 背景音乐音量较低
                    loop_music=True
                )

                logger.info(f"✅ 背景音乐添加完成: {music_stats['output_size_mb']:.2f}MB")
            else:
                # 没有背景音乐，直接移动/复制最终视频
                logger.info("[步骤 6/6] 跳过背景音乐")
                final_video = output_path

                # 复制文件到最终路径
                import shutil
                shutil.copy2(video_with_narration, final_video)
                logger.info(f"✅ 最终视频已生成: {final_video}")

            # ========== 计算总处理时间 ==========
            processing_time = (datetime.now() - start_time).total_seconds()

            # ========== 收集统计信息 ==========
            final_size = os.path.getsize(final_video)
            statistics = {
                'source_videos': len(source_videos),
                'clip_count': len(clip_paths),
                'final_duration': concat_stats['total_duration'],
                'final_size': final_size,
                'final_size_mb': final_size / (1024 * 1024),
                'processing_time': processing_time,
                'has_narration': add_narration and tts_audio_path is not None,
                'has_background_music': background_music_path is not None
            }

            if script_data:
                statistics['script_word_count'] = script_data['word_count']
                statistics['script_estimated_duration'] = script_data['estimated_duration']

            result = {
                'final_video_path': final_video,
                'intermediate_files': intermediate_files,
                'statistics': statistics,
                'processing_time': processing_time
            }

            logger.info(
                f"\n{'='*80}\n"
                f"🎉 视频生成流程完成!\n"
                f"{'='*80}\n"
                f"  最终视频: {final_video}\n"
                f"  文件大小: {statistics['final_size_mb']:.2f}MB\n"
                f"  视频时长: {statistics['final_duration']:.2f}秒\n"
                f"  总处理时间: {processing_time:.2f}秒\n"
                f"  剪辑片段数: {statistics['clip_count']}\n"
                f"  配音状态: {'已添加' if statistics['has_narration'] else '未添加'}\n"
                f"  背景音乐: {'已添加' if statistics['has_background_music'] else '未添加'}\n"
                f"{'='*80}"
            )

            return result

        except Exception as e:
            logger.error(f"视频生成流程失败: {str(e)}", exc_info=True)
            raise ValueError(f"视频生成失败: {str(e)}")

        finally:
            # 可选: 清理中间文件
            # 注意: 在测试阶段建议保留中间文件用于调试
            pass

    async def _extract_clips(
        self,
        source_videos: List[str],
        clip_decision: Dict[str, Any]
    ) -> List[str]:
        """
        从源视频中提取剪辑片段

        Args:
            source_videos: 源视频路径列表
            clip_decision: 剪辑决策

        Returns:
            提取的片段文件路径列表
        """
        clips = clip_decision.get('clips', [])
        clip_paths = []

        for i, clip in enumerate(clips):
            # 获取视频ID对应的源视频路径
            video_id = clip.get('video_id', 'video_001')
            # 简单映射: video_001 -> index 0
            video_index = int(video_id.split('_')[1]) - 1 if '_' in video_id else 0

            if video_index >= len(source_videos):
                logger.warning(
                    f"片段{i+1}的视频索引{video_index}超出范围，使用第一个视频"
                )
                video_index = 0

            source_video = source_videos[video_index]
            start_time = clip.get('start_time', 0)
            end_time = clip.get('end_time', 0)

            # 提取片段
            clip_output = os.path.join(
                settings.temp_dir,
                f"clip_{i+1}_{start_time:.1f}_{end_time:.1f}.mp4"
            )

            clip_path = await self.video_editing.extract_clip(
                video_path=source_video,
                start_time=start_time,
                end_time=end_time,
                output_path=clip_output
            )

            clip_paths.append(clip_path)
            logger.info(
                f"  片段{i+1}: {start_time:.1f}s-{end_time:.1f}s "
                f"({end_time-start_time:.1f}s)"
            )

        return clip_paths

    async def cleanup_intermediate_files(self, intermediate_files: List[str]):
        """
        清理中间文件

        Args:
            intermediate_files: 中间文件路径列表
        """
        logger.info("开始清理中间文件...")
        cleaned_count = 0

        for file_path in intermediate_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    cleaned_count += 1
                    logger.debug(f"已删除: {file_path}")
            except Exception as e:
                logger.warning(f"删除文件失败 {file_path}: {str(e)}")

        logger.info(f"✅ 清理完成: 删除 {cleaned_count}/{len(intermediate_files)} 个文件")


# 单例实例
video_production_orchestrator = VideoProductionOrchestrator()
