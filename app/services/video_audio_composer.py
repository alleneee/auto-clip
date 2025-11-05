"""
视频音频合成服务 - 将剪辑视频与TTS音频合成
职责: 视频与音频的合成、音量平衡、背景音乐混音
"""
import os
from typing import Optional, Dict, Any
from pathlib import Path

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class VideoAudioComposer:
    """视频音频合成服务 - MoviePy 2.x"""

    def __init__(self):
        """初始化视频音频合成服务"""
        self.default_audio_codec = settings.OUTPUT_AUDIO_CODEC
        self.default_video_codec = settings.OUTPUT_VIDEO_CODEC

    async def compose_with_narration(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        audio_volume: float = 1.0,
        original_audio_volume: float = 0.3,
        fade_duration: float = 0.5
    ) -> Dict[str, Any]:
        """
        将视频与配音音频合成

        Args:
            video_path: 源视频路径
            audio_path: 配音音频路径（TTS生成的音频）
            output_path: 输出视频路径
            audio_volume: 配音音量（0.0-2.0，默认1.0）
            original_audio_volume: 原视频音量（0.0-1.0，默认0.3降低原音）
            fade_duration: 淡入淡出时长（秒）

        Returns:
            Dict包含统计信息:
                - output_path: 输出路径
                - output_size: 文件大小
                - video_duration: 视频时长
                - audio_duration: 音频时长

        Raises:
            ValueError: 文件不存在或合成失败
        """
        try:
            if not os.path.exists(video_path):
                raise ValueError(f"视频文件不存在: {video_path}")

            if not os.path.exists(audio_path):
                raise ValueError(f"音频文件不存在: {audio_path}")

            logger.info(
                f"开始视频音频合成:\n"
                f"  视频: {video_path}\n"
                f"  音频: {audio_path}\n"
                f"  输出: {output_path}\n"
                f"  配音音量: {audio_volume}\n"
                f"  原音音量: {original_audio_volume}"
            )

            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # 导入MoviePy
            from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip

            # 加载视频和音频
            video_clip = VideoFileClip(video_path)
            narration_audio = AudioFileClip(audio_path)

            # 调整配音音量（MoviePy 2.x直接调用方法）
            narration_audio = narration_audio.with_volume_scaled(audio_volume)

            # 添加淡入淡出效果
            if fade_duration > 0:
                from moviepy.audio import fx as afx
                narration_audio = narration_audio.with_effects([
                    afx.AudioFadeIn(fade_duration),
                    afx.AudioFadeOut(fade_duration)
                ])

            # 处理原视频音频
            if video_clip.audio is not None and original_audio_volume > 0:
                # 降低原视频音量（MoviePy 2.x直接调用方法）
                original_audio = video_clip.audio.with_volume_scaled(original_audio_volume)

                # 混合原音和配音
                # 确保配音音频长度与视频一致
                if narration_audio.duration < video_clip.duration:
                    # 配音较短，只在开头部分混合
                    composite_audio = CompositeAudioClip([
                        original_audio,
                        narration_audio.with_start(0)
                    ]).with_duration(video_clip.duration)
                else:
                    # 配音较长或相等，裁剪到视频长度
                    narration_audio = narration_audio.subclipped(0, video_clip.duration)
                    composite_audio = CompositeAudioClip([
                        original_audio,
                        narration_audio
                    ])

                # 设置合成音频
                final_clip = video_clip.with_audio(composite_audio)
            else:
                # 没有原音或音量为0，只使用配音
                if narration_audio.duration > video_clip.duration:
                    narration_audio = narration_audio.subclipped(0, video_clip.duration)
                final_clip = video_clip.with_audio(narration_audio)

            # 写入输出文件
            final_clip.write_videofile(
                output_path,
                codec=self.default_video_codec,
                audio_codec=self.default_audio_codec,
                logger=None  # 禁用MoviePy的进度条输出
            )

            # 清理资源
            video_clip.close()
            narration_audio.close()
            if 'composite_audio' in locals():
                composite_audio.close()
            final_clip.close()

            # 获取统计信息
            output_size = os.path.getsize(output_path)

            stats = {
                'output_path': output_path,
                'output_size': output_size,
                'output_size_mb': output_size / (1024 * 1024),
                'video_duration': video_clip.duration,
                'audio_duration': narration_audio.duration
            }

            logger.info(
                f"视频音频合成成功:\n"
                f"  输出文件: {output_path}\n"
                f"  文件大小: {stats['output_size_mb']:.2f}MB\n"
                f"  视频时长: {stats['video_duration']:.2f}秒\n"
                f"  音频时长: {stats['audio_duration']:.2f}秒"
            )

            return stats

        except Exception as e:
            logger.error(f"视频音频合成失败: {str(e)}", exc_info=True)
            # 清理失败的输出文件
            if os.path.exists(output_path):
                os.remove(output_path)
            raise ValueError(f"视频音频合成失败: {str(e)}")

    async def add_background_music(
        self,
        video_path: str,
        music_path: str,
        output_path: str,
        music_volume: float = 0.2,
        loop_music: bool = True
    ) -> Dict[str, Any]:
        """
        为视频添加背景音乐

        Args:
            video_path: 源视频路径
            music_path: 背景音乐路径
            output_path: 输出视频路径
            music_volume: 背景音乐音量（0.0-1.0，默认0.2）
            loop_music: 音乐是否循环（默认True）

        Returns:
            Dict包含统计信息

        Raises:
            ValueError: 文件不存在或添加失败
        """
        try:
            if not os.path.exists(video_path):
                raise ValueError(f"视频文件不存在: {video_path}")

            if not os.path.exists(music_path):
                raise ValueError(f"音乐文件不存在: {music_path}")

            logger.info(
                f"添加背景音乐:\n"
                f"  视频: {video_path}\n"
                f"  音乐: {music_path}\n"
                f"  输出: {output_path}\n"
                f"  音乐音量: {music_volume}\n"
                f"  循环: {loop_music}"
            )

            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip

            # 加载视频和音乐
            video_clip = VideoFileClip(video_path)
            music_clip = AudioFileClip(music_path)

            # 调整音乐音量（MoviePy 2.x直接调用方法）
            music_clip = music_clip.with_volume_scaled(music_volume)

            # 处理音乐长度
            if loop_music and music_clip.duration < video_clip.duration:
                # 循环音乐直到视频结束
                from moviepy import concatenate_audioclips
                loops_needed = int(video_clip.duration / music_clip.duration) + 1
                music_clip = concatenate_audioclips([music_clip] * loops_needed)

            # 裁剪音乐到视频长度
            music_clip = music_clip.subclipped(0, video_clip.duration)

            # 混合原音和背景音乐
            if video_clip.audio is not None:
                composite_audio = CompositeAudioClip([
                    video_clip.audio,
                    music_clip
                ])
            else:
                composite_audio = music_clip

            # 设置合成音频
            final_clip = video_clip.with_audio(composite_audio)

            # 写入输出文件
            final_clip.write_videofile(
                output_path,
                codec=self.default_video_codec,
                audio_codec=self.default_audio_codec,
                logger=None
            )

            # 清理资源
            video_clip.close()
            music_clip.close()
            composite_audio.close()
            final_clip.close()

            # 统计信息
            output_size = os.path.getsize(output_path)

            stats = {
                'output_path': output_path,
                'output_size': output_size,
                'output_size_mb': output_size / (1024 * 1024),
                'video_duration': video_clip.duration
            }

            logger.info(
                f"背景音乐添加成功:\n"
                f"  输出文件: {output_path}\n"
                f"  文件大小: {stats['output_size_mb']:.2f}MB"
            )

            return stats

        except Exception as e:
            logger.error(f"添加背景音乐失败: {str(e)}", exc_info=True)
            if os.path.exists(output_path):
                os.remove(output_path)
            raise ValueError(f"添加背景音乐失败: {str(e)}")


# 单例实例
video_audio_composer = VideoAudioComposer()
