"""
视频处理相关服务抽象接口 (SOLID: 依赖倒置原则)
"""
from typing import Protocol, Tuple, Dict, Any


class IVideoPreprocessor(Protocol):
    """视频预处理服务接口"""

    async def compress_and_encode(
        self,
        video_path: str
    ) -> Tuple[str, str, float]:
        """
        压缩视频并转换为base64

        Args:
            video_path: 原始视频路径

        Returns:
            Tuple[压缩后路径, base64编码, 压缩率]
        """
        ...


class IVideoCompressionService(Protocol):
    """视频压缩服务接口"""

    async def compress_video(
        self,
        input_path: str,
        output_path: str,
        profile_name: str = "balanced"
    ) -> Tuple[str, Dict[str, Any]]:
        """
        压缩视频

        Args:
            input_path: 输入路径
            output_path: 输出路径
            profile_name: 压缩配置名称

        Returns:
            Tuple[压缩后路径, 统计信息]
        """
        ...


class IAudioExtractor(Protocol):
    """音频提取服务接口"""

    async def extract_audio(
        self,
        video_path: str,
        output_path: str
    ) -> str:
        """
        从视频提取音频

        Args:
            video_path: 视频文件路径
            output_path: 输出音频路径

        Returns:
            音频文件路径
        """
        ...
