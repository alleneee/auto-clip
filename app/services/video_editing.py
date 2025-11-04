"""
视频剪辑服务
使用 MoviePy 2.x 进行视频剪辑、拼接和后处理
"""
import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

# MoviePy 2.x 标准导入
from moviepy import VideoFileClip, concatenate_videoclips, CompositeVideoClip, vfx

from app.config import settings
from app.models.batch_processing import ClipSegment
from app.utils.logger import logger


class VideoEditingService:
    """视频剪辑服务 - MoviePy 2.x"""

    def __init__(self):
        """初始化视频剪辑服务"""
        self.output_quality_map = {
            'low': {'bitrate': '500k', 'preset': 'ultrafast'},
            'medium': {'bitrate': '1500k', 'preset': 'fast'},
            'high': {'bitrate': '3000k', 'preset': 'medium'},
            'source': None  # 保持原始质量
        }

    async def extract_clip(
        self,
        video_path: str,
        start_time: float,
        end_time: float,
        output_path: Optional[str] = None
    ) -> str:
        """
        从视频中提取片段

        Args:
            video_path: 源视频路径
            start_time: 开始时间（秒）
            end_time: 结束时间（秒）
            output_path: 输出路径（可选）

        Returns:
            str: 剪辑片段路径

        Raises:
            ValueError: 时间范围无效或视频处理失败
        """
        if not os.path.exists(video_path):
            raise ValueError(f"源视频不存在: {video_path}")

        if start_time >= end_time:
            raise ValueError(f"无效的时间范围: {start_time} >= {end_time}")

        # 生成输出路径
        if output_path is None:
            base_name = Path(video_path).stem
            output_path = os.path.join(
                settings.temp_dir,
                f"{base_name}_clip_{start_time:.1f}_{end_time:.1f}.mp4"
            )

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        try:
            logger.info(
                f"提取视频片段: {video_path}\n"
                f"  时间范围: {start_time:.2f}s - {end_time:.2f}s\n"
                f"  输出: {output_path}"
            )

            # 加载视频并提取子片段 (MoviePy 2.x 使用 subclipped)
            with VideoFileClip(video_path) as video:
                # 验证时间范围
                if end_time > video.duration:
                    logger.warning(
                        f"结束时间 {end_time}s 超过视频时长 {video.duration}s，"
                        f"调整为 {video.duration}s"
                    )
                    end_time = video.duration

                # MoviePy 2.x: subclipped() 方法
                clip = video.subclipped(start_time, end_time)

                # MoviePy 2.x: write_videofile 不再支持 verbose/logger 参数
                clip.write_videofile(
                    output_path,
                    codec=settings.OUTPUT_VIDEO_CODEC,
                    audio_codec=settings.OUTPUT_AUDIO_CODEC
                )

            logger.info(f"视频片段提取成功: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"提取视频片段失败: {str(e)}", exc_info=True)
            # 清理失败的输出文件
            if output_path and os.path.exists(output_path):
                os.remove(output_path)
            raise ValueError(f"视频剪辑失败: {str(e)}")

    async def concatenate_clips(
        self,
        clip_paths: List[str],
        output_path: str,
        output_quality: str = 'high',
        add_transitions: bool = False
    ) -> Tuple[str, Dict[str, Any]]:
        """
        拼接多个视频片段

        Args:
            clip_paths: 视频片段路径列表
            output_path: 输出路径
            output_quality: 输出质量 (low/medium/high/source)
            add_transitions: 是否添加转场效果

        Returns:
            Tuple[str, Dict[str, Any]]: (输出路径, 统计信息)

        Raises:
            ValueError: 片段列表为空或拼接失败
        """
        if not clip_paths:
            raise ValueError("视频片段列表为空")

        # 验证所有片段文件存在
        for path in clip_paths:
            if not os.path.exists(path):
                raise ValueError(f"视频片段不存在: {path}")

        start_time = datetime.now()

        try:
            logger.info(
                f"开始拼接视频片段:\n"
                f"  片段数量: {len(clip_paths)}\n"
                f"  输出质量: {output_quality}\n"
                f"  输出路径: {output_path}"
            )

            # 加载所有视频片段
            clips = [VideoFileClip(path) for path in clip_paths]

            # 计算总时长
            total_duration = sum(clip.duration for clip in clips)

            # 拼接视频
            if add_transitions:
                # 添加转场效果（淡入淡出）
                transition_duration = 0.5  # 转场时长（秒）

                # 为每个片段添加淡入淡出效果
                clips_with_transitions = []
                for i, clip in enumerate(clips):
                    # 第一个片段：只淡入
                    if i == 0:
                        clip = clip.with_effects([vfx.FadeIn(transition_duration)])
                    # 最后一个片段：只淡出
                    elif i == len(clips) - 1:
                        clip = clip.with_effects([vfx.FadeOut(transition_duration)])
                    # 中间片段：淡入+淡出
                    else:
                        clip = clip.with_effects([
                            vfx.FadeIn(transition_duration),
                            vfx.FadeOut(transition_duration)
                        ])
                    clips_with_transitions.append(clip)

                # 使用compose方法拼接，允许重叠实现交叉淡化
                final_clip = concatenate_videoclips(clips_with_transitions, method="compose")
            else:
                final_clip = concatenate_videoclips(clips)

            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # 获取输出质量设置
            quality_settings = self.output_quality_map.get(output_quality)

            # MoviePy 2.x: write_videofile 不再支持 verbose/logger 参数
            if quality_settings:
                final_clip.write_videofile(
                    output_path,
                    codec=settings.OUTPUT_VIDEO_CODEC,
                    audio_codec=settings.OUTPUT_AUDIO_CODEC,
                    bitrate=quality_settings['bitrate'],
                    preset=quality_settings['preset']
                )
            else:
                # 保持原始质量
                final_clip.write_videofile(
                    output_path,
                    codec=settings.OUTPUT_VIDEO_CODEC,
                    audio_codec=settings.OUTPUT_AUDIO_CODEC
                )

            # 清理片段对象
            for clip in clips:
                clip.close()
            final_clip.close()

            # 计算统计信息
            processing_time = (datetime.now() - start_time).total_seconds()
            output_size = os.path.getsize(output_path)

            stats = {
                'clip_count': len(clip_paths),
                'total_duration': total_duration,
                'output_size': output_size,
                'output_size_mb': output_size / (1024 * 1024),
                'processing_time': processing_time,
                'output_quality': output_quality
            }

            logger.info(
                f"视频拼接成功:\n"
                f"  片段数: {stats['clip_count']}\n"
                f"  总时长: {stats['total_duration']:.2f}秒\n"
                f"  文件大小: {stats['output_size_mb']:.2f}MB\n"
                f"  处理耗时: {stats['processing_time']:.2f}秒"
            )

            return output_path, stats

        except Exception as e:
            logger.error(f"拼接视频失败: {str(e)}", exc_info=True)
            # 清理失败的输出文件
            if os.path.exists(output_path):
                os.remove(output_path)
            raise ValueError(f"视频拼接失败: {str(e)}")

    async def process_clip_plan(
        self,
        video_paths: List[str],
        segments: List[ClipSegment],
        output_path: str,
        output_quality: str = 'high'
    ) -> Tuple[str, Dict[str, Any]]:
        """
        根据剪辑方案处理视频

        Args:
            video_paths: 源视频路径列表（索引对应 ClipSegment.video_index）
            segments: 剪辑片段列表
            output_path: 最终输出路径
            output_quality: 输出质量

        Returns:
            Tuple[str, Dict[str, Any]]: (输出路径, 统计信息)

        Raises:
            ValueError: 视频列表为空、索引超出范围或处理失败
        """
        if not video_paths:
            raise ValueError("源视频列表为空")

        if not segments:
            raise ValueError("剪辑片段列表为空")

        logger.info(
            f"开始处理剪辑方案:\n"
            f"  源视频数: {len(video_paths)}\n"
            f"  剪辑片段数: {len(segments)}\n"
            f"  输出: {output_path}"
        )

        # 临时片段文件路径列表
        temp_clip_paths: List[str] = []

        try:
            # 按优先级排序片段
            sorted_segments = sorted(segments, key=lambda s: s.priority, reverse=True)

            # 提取每个片段
            for idx, segment in enumerate(sorted_segments):
                # 验证视频索引
                if segment.video_index >= len(video_paths):
                    raise ValueError(
                        f"片段 {idx} 的视频索引 {segment.video_index} "
                        f"超出范围 (0-{len(video_paths)-1})"
                    )

                source_video = video_paths[segment.video_index]

                # 生成临时片段路径
                temp_clip_path = os.path.join(
                    settings.temp_dir,
                    f"segment_{idx}_{segment.start_time:.1f}_{segment.end_time:.1f}.mp4"
                )

                # 提取片段
                clip_path = await self.extract_clip(
                    source_video,
                    segment.start_time,
                    segment.end_time,
                    temp_clip_path
                )

                temp_clip_paths.append(clip_path)

            # 拼接所有片段
            final_path, stats = await self.concatenate_clips(
                temp_clip_paths,
                output_path,
                output_quality
            )

            # 添加剪辑方案信息到统计
            stats['segment_count'] = len(segments)
            stats['source_video_count'] = len(video_paths)
            stats['segments_info'] = [
                {
                    'video_index': seg.video_index,
                    'time_range': f"{seg.start_time:.2f}s - {seg.end_time:.2f}s",
                    'duration': seg.duration,
                    'reason': seg.reason
                }
                for seg in sorted_segments
            ]

            return final_path, stats

        except Exception as e:
            logger.error(f"处理剪辑方案失败: {str(e)}", exc_info=True)
            raise

        finally:
            # 清理临时片段文件
            for temp_path in temp_clip_paths:
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                        logger.debug(f"清理临时片段: {temp_path}")
                except Exception as e:
                    logger.warning(f"清理临时片段失败 {temp_path}: {str(e)}")

    async def get_video_duration(self, video_path: str) -> float:
        """
        获取视频时长

        Args:
            video_path: 视频文件路径

        Returns:
            float: 视频时长（秒）
        """
        if not os.path.exists(video_path):
            raise ValueError(f"视频文件不存在: {video_path}")

        try:
            with VideoFileClip(video_path) as video:
                return video.duration
        except Exception as e:
            logger.error(f"获取视频时长失败: {str(e)}")
            raise ValueError(f"无法读取视频: {str(e)}")


# 单例实例
video_editing_service = VideoEditingService()
