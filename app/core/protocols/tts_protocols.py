"""
文本转语音(TTS)服务抽象接口 (SOLID: 依赖倒置原则)
"""
from typing import Protocol, Optional


class ITTSService(Protocol):
    """文本转语音(TTS)服务接口 (支持多种TTS服务提供商)"""

    async def synthesize_speech(
        self,
        text: str,
        voice: Optional[str] = None,
        output_format: str = "mp3"
    ) -> bytes:
        """
        将文本转换为语音

        Args:
            text: 要转换的文本
            voice: 语音模型/音色 (如: "zhiyan", "longxiaochun"等)
            output_format: 输出格式 (mp3/wav等)

        Returns:
            音频数据(bytes)
        """
        ...

    async def synthesize_to_file(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None,
        output_format: str = "mp3"
    ) -> str:
        """
        将文本转换为语音并保存到文件

        Args:
            text: 要转换的文本
            output_path: 输出文件路径
            voice: 语音模型/音色
            output_format: 输出格式

        Returns:
            保存的文件路径
        """
        ...
