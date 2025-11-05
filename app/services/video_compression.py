"""
视频压缩服务 - 符合单一职责原则
职责: 视频压缩业务编排和配置管理（业务层）
底层操作: 使用 video_utils 工具函数

重构说明：
- 使用 video_utils.get_video_info() 获取视频信息
- 保留业务层的压缩配置管理和策略选择
- 底层 FFmpeg 操作由 Service 管理（因为有复杂的业务配置）
"""
import os
import subprocess
import asyncio
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from app.config import settings
from app.models.video_source import (
    CompressionProfile,
    COMPRESSION_PROFILES,
    get_dynamic_compression_profile
)
from app.utils.logger import logger
from app.utils.video_utils import get_video_info


class VideoMetadata:
    """视频元信息"""

    def __init__(self, data: Dict[str, Any]):
        self.duration: float = float(data.get('duration', 0))
        self.width: int = int(data.get('width', 0))
        self.height: int = int(data.get('height', 0))
        self.fps: float = float(data.get('fps', 0))
        self.bitrate: int = int(data.get('bitrate', 0))
        self.codec: str = data.get('codec', 'unknown')
        self.file_size: int = data.get('file_size', 0)

    @property
    def resolution(self) -> str:
        """分辨率字符串"""
        return f"{self.width}x{self.height}"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'duration': self.duration,
            'resolution': self.resolution,
            'fps': self.fps,
            'bitrate': self.bitrate,
            'codec': self.codec,
            'file_size': self.file_size
        }


class VideoCompressionService:
    """视频压缩服务"""

    def __init__(self):
        self.ffmpeg_path = "ffmpeg"

    async def get_video_metadata(self, video_path: str) -> VideoMetadata:
        """
        获取视频元信息（业务层封装）

        Args:
            video_path: 视频文件路径

        Returns:
            VideoMetadata: 视频元信息

        Raises:
            ValueError: 视频文件不存在或格式错误
        """
        if not os.path.exists(video_path):
            raise ValueError(f"视频文件不存在: {video_path}")

        try:
            # 使用 video_utils 获取基本信息
            info = get_video_info(video_path)

            # 转换为 VideoMetadata 业务模型
            # 注意：bitrate 和 codec 信息在简化版中不可用
            # 如果业务需要，可以保留 ffprobe 调用，或者从 VideoMetadata 中移除这些字段
            metadata = {
                'duration': info['duration'],
                'width': info['width'],
                'height': info['height'],
                'fps': info['fps'],
                'bitrate': 0,  # 简化版不提供
                'codec': 'unknown',  # 简化版不提供
                'file_size': info['size_bytes']
            }

            return VideoMetadata(metadata)

        except Exception as e:
            logger.error(f"获取视频元信息失败: {str(e)}", exc_info=True)
            raise ValueError(f"无法解析视频文件: {str(e)}")

    def select_compression_profile(
        self,
        metadata: VideoMetadata,
        profile_name: Optional[str] = None
    ) -> CompressionProfile:
        """
        选择压缩配置

        Args:
            metadata: 视频元信息
            profile_name: 指定的配置名称（aggressive/balanced/conservative/dynamic）

        Returns:
            CompressionProfile: 压缩配置
        """
        if profile_name == "dynamic" or profile_name is None:
            # 动态选择：根据视频时长
            return get_dynamic_compression_profile(metadata.duration)

        # 使用指定的配置
        if profile_name in COMPRESSION_PROFILES:
            return COMPRESSION_PROFILES[profile_name]

        # 默认使用 balanced
        logger.warning(f"未知的压缩配置: {profile_name}，使用默认配置 balanced")
        return COMPRESSION_PROFILES["balanced"]

    async def compress_video(
        self,
        input_path: str,
        output_path: str,
        profile: Optional[CompressionProfile] = None,
        profile_name: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        压缩视频

        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径
            profile: 压缩配置对象
            profile_name: 压缩配置名称（如果 profile 为 None）

        Returns:
            Tuple[str, Dict[str, Any]]: (输出路径, 压缩统计信息)

        Raises:
            ValueError: 视频文件不存在或压缩失败
        """
        start_time = datetime.now()

        # 获取原始视频元信息
        original_metadata = await self.get_video_metadata(input_path)

        # 检查视频时长限制
        if original_metadata.duration > settings.MAX_VIDEO_DURATION:
            raise ValueError(
                f"视频时长 {original_metadata.duration}秒 超过最大限制 "
                f"{settings.MAX_VIDEO_DURATION}秒"
            )

        # 选择压缩配置
        if profile is None:
            profile = self.select_compression_profile(original_metadata, profile_name)

        logger.info(
            f"开始压缩视频: {input_path} → {output_path} "
            f"(策略: {profile.name})"
        )

        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 解析目标分辨率
        resolution_map = {
            '480p': '854:480',
            '720p': '1280:720',
            '1080p': '1920:1080'
        }
        target_resolution = resolution_map.get(profile.max_resolution, '1280:720')

        # 构建 FFmpeg 命令
        cmd = [
            self.ffmpeg_path,
            "-i", input_path,
            "-c:v", profile.video_codec,
            "-preset", profile.preset,
            "-crf", str(profile.crf),
            "-b:v", profile.video_bitrate,
            "-maxrate", profile.video_bitrate,
            "-bufsize", f"{int(profile.video_bitrate.rstrip('k')) * 2}k",
            "-vf", f"scale={target_resolution}:force_original_aspect_ratio=decrease,fps={profile.target_fps}",
            "-c:a", "aac",
            "-b:a", profile.audio_bitrate,
            "-ar", str(profile.audio_sample_rate),
            "-movflags", "+faststart",  # 优化在线播放
            "-y",  # 覆盖输出文件
            output_path
        ]

        try:
            # 执行压缩
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode()
                logger.error(f"FFmpeg 压缩失败: {error_msg}")
                raise ValueError(f"视频压缩失败: {error_msg}")

            # 获取压缩后的元信息
            compressed_metadata = await self.get_video_metadata(output_path)

            # 计算压缩统计
            processing_time = (datetime.now() - start_time).total_seconds()
            compression_ratio = (
                1 - (compressed_metadata.file_size / original_metadata.file_size)
            ) if original_metadata.file_size > 0 else 0

            stats = {
                'original_size': original_metadata.file_size,
                'compressed_size': compressed_metadata.file_size,
                'compression_ratio': compression_ratio,
                'size_reduction_mb': (
                    original_metadata.file_size - compressed_metadata.file_size
                ) / (1024 * 1024),
                'original_duration': original_metadata.duration,
                'compressed_duration': compressed_metadata.duration,
                'original_resolution': original_metadata.resolution,
                'compressed_resolution': compressed_metadata.resolution,
                'original_fps': original_metadata.fps,
                'compressed_fps': compressed_metadata.fps,
                'profile_used': profile.name,
                'processing_time': processing_time
            }

            logger.info(
                f"视频压缩成功: {input_path} → {output_path}\n"
                f"  原始大小: {original_metadata.file_size / (1024*1024):.2f}MB\n"
                f"  压缩大小: {compressed_metadata.file_size / (1024*1024):.2f}MB\n"
                f"  压缩率: {compression_ratio * 100:.1f}%\n"
                f"  耗时: {processing_time:.2f}秒"
            )

            return output_path, stats

        except Exception as e:
            logger.error(f"视频压缩异常: {str(e)}", exc_info=True)
            # 清理失败的输出文件
            if os.path.exists(output_path):
                os.remove(output_path)
            raise

    async def validate_video_duration(self, video_path: str) -> bool:
        """
        验证视频时长是否在允许范围内

        Args:
            video_path: 视频文件路径

        Returns:
            bool: 是否有效
        """
        try:
            metadata = await self.get_video_metadata(video_path)
            return metadata.duration <= settings.MAX_VIDEO_DURATION
        except Exception as e:
            logger.error(f"验证视频时长失败: {str(e)}")
            return False


# 单例实例
video_compression_service = VideoCompressionService()
