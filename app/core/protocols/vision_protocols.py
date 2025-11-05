"""
视觉分析服务抽象接口 (SOLID: 依赖倒置原则)
"""
from typing import Protocol, Optional


class IVisionAnalysisService(Protocol):
    """视觉分析服务接口 (支持多种AI服务提供商)"""

    async def analyze_from_url(
        self,
        video_url: str,
        prompt: Optional[str] = None
    ) -> str:
        """
        从网络URL分析视频视觉内容

        Args:
            video_url: 视频的网络URL (HTTP/HTTPS)
            prompt: 自定义提示词

        Returns:
            视觉分析结果文本
        """
        ...

    async def analyze_from_base64(
        self,
        video_base64: str,
        prompt: Optional[str] = None
    ) -> str:
        """
        从base64编码分析视频视觉内容

        Args:
            video_base64: 视频的base64编码字符串
            prompt: 自定义提示词

        Returns:
            视觉分析结果文本
        """
        ...
