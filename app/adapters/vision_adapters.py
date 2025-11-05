"""
视频视觉分析适配器 - 符合依赖倒置原则
让现有的视觉AI客户端适配抽象接口
"""
from typing import Optional

from app.utils.ai_clients.dashscope_client import DashScopeClient
from app.core.protocols.vision_protocols import IVisionAnalysisService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DashScopeVisionAdapter:
    """
    DashScope视觉分析适配器 (OCP: 开闭原则)
    适配器模式 - 让DashScopeClient实现IVisionAnalysisService接口
    便于后续替换为其他AI服务提供商（Google Vision, AWS Rekognition等）
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化适配器

        Args:
            api_key: DashScope API密钥
        """
        self.client = DashScopeClient(api_key=api_key)
        logger.info("dashscope_vision_adapter_initialized")

    async def analyze_from_url(
        self,
        video_url: str,
        prompt: Optional[str] = None
    ) -> str:
        """
        从网络URL分析视频（适配接口）

        Args:
            video_url: 视频网络URL
            prompt: 自定义提示词

        Returns:
            视觉分析结果
        """
        return await self.client.analyze_video_visual(
            video_url=video_url,
            prompt=prompt
        )

    async def analyze_from_base64(
        self,
        video_base64: str,
        prompt: Optional[str] = None
    ) -> str:
        """
        从base64编码分析视频（适配接口）

        Args:
            video_base64: base64编码字符串
            prompt: 自定义提示词

        Returns:
            视觉分析结果
        """
        return await self.client.analyze_video_visual_base64(
            video_base64=video_base64,
            prompt=prompt
        )
