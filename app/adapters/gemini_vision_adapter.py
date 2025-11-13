"""
Gemini视频视觉分析适配器 - 符合依赖倒置原则
让Gemini客户端适配抽象接口
"""
from typing import Optional

from app.utils.ai_clients.gemini_client import GeminiClient
from app.utils.ai_clients.gemini_openai_compatible_client import GeminiOpenAICompatibleClient
from app.core.protocols.vision_protocols import IVisionAnalysisService
from app.utils.logger import get_logger
from app.config import settings

logger = get_logger(__name__)


class GeminiVisionAdapter:
    """
    Gemini视觉分析适配器 (OCP: 开闭原则)

    适配器模式 - 让GeminiClient实现IVisionAnalysisService接口
    便于在项目中替换DashScope为Gemini，或在两者之间切换

    特点：
    - 支持自定义base_url（用于代理服务）
    - 兼容项目现有的视觉分析接口
    - 支持本地文件和base64两种输入方式
    - 原生视频理解能力（Gemini 2.0）
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 120.0,
        use_openai_format: Optional[bool] = None
    ):
        """
        初始化适配器

        Args:
            api_key: Gemini API密钥（默认从配置读取）
            base_url: API基础URL（支持自定义代理地址）
            model: 模型名称（默认gemini-2.0-flash-exp）
            timeout: 请求超时时间（秒）
            use_openai_format: 是否使用OpenAI兼容格式（自动检测或手动指定）
        """
        # 自动检测是否使用OpenAI兼容格式
        if use_openai_format is None:
            # 如果base_url包含chat/completions，则使用OpenAI格式
            effective_base_url = base_url or settings.GEMINI_BASE_URL or ""
            use_openai_format = "chat/completions" in effective_base_url.lower()

        if use_openai_format:
            logger.info("using_openai_compatible_format", base_url=effective_base_url)
            self.client = GeminiOpenAICompatibleClient(
                api_key=api_key,
                base_url=base_url,
                model=model,
                timeout=timeout
            )
        else:
            logger.info("using_gemini_native_format")
            self.client = GeminiClient(
                api_key=api_key,
                base_url=base_url,
                model=model,
                timeout=timeout
            )

        logger.info(
            "gemini_vision_adapter_initialized",
            model=self.client.model,
            base_url=self.client.base_url,
            client_type=type(self.client).__name__
        )

    async def analyze_from_url(
        self,
        video_url: str,
        prompt: Optional[str] = None
    ) -> str:
        """
        从网络URL分析视频（适配接口）

        注意：Gemini API不直接支持URL，需要先下载视频
        此方法会抛出NotImplementedError
        建议使用analyze_from_path或analyze_from_base64

        Args:
            video_url: 视频网络URL
            prompt: 自定义提示词

        Returns:
            视觉分析结果

        Raises:
            NotImplementedError: Gemini不支持直接URL访问
        """
        logger.warning(
            "gemini_url_not_supported",
            message="Gemini不支持直接从URL分析视频，请使用analyze_from_path或analyze_from_base64"
        )
        raise NotImplementedError(
            "Gemini API不支持直接从URL分析视频。"
            "请先下载视频，然后使用analyze_from_path()方法。"
        )

    async def analyze_from_base64(
        self,
        video_base64: str,
        prompt: Optional[str] = None,
        mime_type: str = "video/mp4"
    ) -> str:
        """
        从base64编码分析视频（适配接口）

        Args:
            video_base64: base64编码字符串（不包含data URI前缀）
            prompt: 自定义提示词
            mime_type: 视频MIME类型

        Returns:
            视觉分析结果
        """
        default_prompt = "请详细分析这个视频的内容，包括场景、人物、动作、情感等元素。"

        return await self.client.analyze_video_from_base64(
            video_base64=video_base64,
            prompt=prompt or default_prompt,
            mime_type=mime_type
        )

    async def analyze_from_path(
        self,
        video_path: str,
        prompt: Optional[str] = None
    ) -> str:
        """
        从本地路径分析视频（扩展接口）

        Args:
            video_path: 本地视频文件路径
            prompt: 自定义提示词

        Returns:
            视觉分析结果
        """
        default_prompt = "请详细分析这个视频的内容，包括场景、人物、动作、情感等元素。"

        return await self.client.analyze_video_from_path(
            video_path=video_path,
            prompt=prompt or default_prompt
        )


# 导出便捷函数
def create_gemini_vision_adapter(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    **kwargs
) -> GeminiVisionAdapter:
    """
    创建Gemini视觉分析适配器的便捷函数

    Args:
        api_key: Gemini API密钥
        base_url: API基础URL（支持自定义代理）
        **kwargs: 其他参数

    Returns:
        GeminiVisionAdapter实例
    """
    return GeminiVisionAdapter(api_key=api_key, base_url=base_url, **kwargs)
