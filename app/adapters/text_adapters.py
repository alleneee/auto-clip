"""
文本生成适配器 - 符合依赖倒置原则
让现有的文本生成AI客户端适配抽象接口
"""
from typing import Optional

from app.utils.ai_clients.dashscope_client import DashScopeClient
from app.core.protocols.text_protocols import ITextGenerationService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DashScopeTextAdapter:
    """
    DashScope文本生成适配器 (OCP: 开闭原则)
    适配器模式 - 让DashScopeClient实现ITextGenerationService接口
    便于后续替换为其他LLM服务提供商（OpenAI, Claude, Gemini等）
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化适配器

        Args:
            api_key: DashScope API密钥
        """
        self.client = DashScopeClient(api_key=api_key)
        logger.info("dashscope_text_adapter_initialized")

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        生成文本（适配接口）

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词

        Returns:
            生成的文本
        """
        return await self.client.chat(
            prompt=prompt,
            system_prompt=system_prompt
        )
