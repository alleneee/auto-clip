"""
文本生成服务抽象接口 (SOLID: 依赖倒置原则)
"""
from typing import Protocol, Optional


class ITextGenerationService(Protocol):
    """文本生成服务接口"""

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        生成文本

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词

        Returns:
            生成的文本
        """
        ...
