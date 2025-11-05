"""
文本转语音(TTS)适配器 - 符合依赖倒置原则
让现有的TTS客户端适配抽象接口
"""
from typing import Optional
import aiofiles

from app.utils.ai_clients.dashscope_client import DashScopeClient
from app.core.protocols.tts_protocols import ITTSService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DashScopeTTSAdapter:
    """
    DashScope文本转语音适配器 (OCP: 开闭原则)
    适配器模式 - 让DashScopeClient实现ITTSService接口
    便于后续替换为其他TTS服务提供商（Azure TTS, Google TTS等）

    注意: 需要在DashScopeClient中实现synthesize_speech_*方法
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化适配器

        Args:
            api_key: DashScope API密钥
        """
        self.client = DashScopeClient(api_key=api_key)
        logger.info("dashscope_tts_adapter_initialized")

    async def synthesize_speech(
        self,
        text: str,
        voice: Optional[str] = None,
        output_format: str = "mp3"
    ) -> bytes:
        """
        将文本转换为语音（适配接口）

        Args:
            text: 要转换的文本
            voice: 语音模型/音色 (默认使用longwan女声)
            output_format: 输出格式 (mp3/wav等)

        Returns:
            音频数据(bytes)
        """
        # 调用DashScopeClient的TTS方法
        return await self.client.synthesize_speech(
            text=text,
            voice=voice or "Cherry",  # 使用Cherry作为默认音色 (qwen3-tts-flash)
            output_format=output_format
        )

    async def synthesize_to_file(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None,
        output_format: str = "mp3"
    ) -> str:
        """
        将文本转换为语音并保存到文件（适配接口）

        Args:
            text: 要转换的文本
            output_path: 输出文件路径
            voice: 语音模型/音色
            output_format: 输出格式

        Returns:
            保存的文件路径
        """
        # 获取音频数据
        audio_data = await self.synthesize_speech(
            text=text,
            voice=voice,
            output_format=output_format
        )

        # 异步写入文件
        async with aiofiles.open(output_path, 'wb') as f:
            await f.write(audio_data)

        logger.info(f"tts_audio_saved_to_file: {output_path}")
        return output_path
