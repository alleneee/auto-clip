"""
视频剪辑服务 - 符合单一职责原则
职责: 视频剪辑业务编排（业务层）
底层操作: 使用 video_utils 工具函数

重构说明：
- extract_clip() 使用 video_utils.extract_video_clip()
- concatenate_clips() 使用 video_utils.concatenate_video_clips()
- get_video_duration() 使用 video_utils.get_video_info()
- Service层专注业务编排、参数验证、异常处理
"""
import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

from app.config import settings
from app.models.batch_processing import ClipSegment
from app.utils.logger import logger
from app.utils.video_utils import extract_video_clip, concatenate_video_clips, get_video_info


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
        从视频中提取片段（业务编排层）

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
        # 业务层参数验证
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

            # 调用底层工具函数
            result_path = extract_video_clip(
                video_path=video_path,
                start_time=start_time,
                end_time=end_time,
                output_path=output_path,
                codec=settings.OUTPUT_VIDEO_CODEC,
                audio_codec=settings.OUTPUT_AUDIO_CODEC
            )

            logger.info(f"视频片段提取成功: {result_path}")
            return result_path

        except RuntimeError as e:
            # 业务异常转换
            logger.error(f"提取视频片段失败: {str(e)}", exc_info=True)
            # 清理失败的输出文件
            if output_path and os.path.exists(output_path):
                os.remove(output_path)
            raise ValueError(f"视频剪辑失败: {str(e)}")
        except Exception as e:
            logger.error(f"提取视频片段异常: {str(e)}", exc_info=True)
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
        拼接多个视频片段（业务编排层）

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
        # 业务层参数验证
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
                f"  添加转场: {add_transitions}\n"
                f"  输出路径: {output_path}"
            )

            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # 如果不需要转场效果，使用工具函数（简单快速）
            if not add_transitions:
                # 调用底层工具函数
                result_path = concatenate_video_clips(
                    clip_paths=clip_paths,
                    output_path=output_path,
                    method="compose",
                    codec=settings.OUTPUT_VIDEO_CODEC,
                    audio_codec=settings.OUTPUT_AUDIO_CODEC
                )

                # 计算统计信息
                processing_time = (datetime.now() - start_time).total_seconds()
                output_size = os.path.getsize(result_path)

                # 计算总时长（通过读取输出视频）
                info = get_video_info(result_path)
                total_duration = info['duration']

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

                return result_path, stats

            else:
                # 带转场效果需要使用 MoviePy（业务功能）
                from moviepy import VideoFileClip, concatenate_videoclips, vfx

                clips = [VideoFileClip(path) for path in clip_paths]
                total_duration = sum(clip.duration for clip in clips)

                # 添加转场效果（淡入淡出）
                transition_duration = 0.5
                clips_with_transitions = []

                for i, clip in enumerate(clips):
                    if i == 0:
                        clip = clip.with_effects([vfx.FadeIn(transition_duration)])
                    elif i == len(clips) - 1:
                        clip = clip.with_effects([vfx.FadeOut(transition_duration)])
                    else:
                        clip = clip.with_effects([
                            vfx.FadeIn(transition_duration),
                            vfx.FadeOut(transition_duration)
                        ])
                    clips_with_transitions.append(clip)

                final_clip = concatenate_videoclips(clips_with_transitions, method="compose")

                # 获取输出质量设置
                quality_settings = self.output_quality_map.get(output_quality)

                if quality_settings:
                    final_clip.write_videofile(
                        output_path,
                        codec=settings.OUTPUT_VIDEO_CODEC,
                        audio_codec=settings.OUTPUT_AUDIO_CODEC,
                        bitrate=quality_settings['bitrate'],
                        preset=quality_settings['preset']
                    )
                else:
                    final_clip.write_videofile(
                        output_path,
                        codec=settings.OUTPUT_VIDEO_CODEC,
                        audio_codec=settings.OUTPUT_AUDIO_CODEC
                    )

                # 清理
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
                    f"视频拼接成功（带转场）:\n"
                    f"  片段数: {stats['clip_count']}\n"
                    f"  总时长: {stats['total_duration']:.2f}秒\n"
                    f"  文件大小: {stats['output_size_mb']:.2f}MB\n"
                    f"  处理耗时: {stats['processing_time']:.2f}秒"
                )

                return output_path, stats

        except RuntimeError as e:
            logger.error(f"拼接视频失败: {str(e)}", exc_info=True)
            if os.path.exists(output_path):
                os.remove(output_path)
            raise ValueError(f"视频拼接失败: {str(e)}")
        except Exception as e:
            logger.error(f"拼接视频异常: {str(e)}", exc_info=True)
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
        获取视频时长（业务层封装）

        Args:
            video_path: 视频文件路径

        Returns:
            float: 视频时长（秒）

        Raises:
            ValueError: 视频文件不存在或读取失败
        """
        if not os.path.exists(video_path):
            raise ValueError(f"视频文件不存在: {video_path}")

        try:
            # 使用 video_utils 获取视频信息
            info = get_video_info(video_path)
            return info['duration']
        except Exception as e:
            logger.error(f"获取视频时长失败: {str(e)}")
            raise ValueError(f"无法读取视频: {str(e)}")


# 单例实例
video_editing_service = VideoEditingService()
