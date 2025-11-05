"""
音频语音识别适配器 - 符合依赖倒置原则
让现有的语音识别客户端适配抽象接口
"""
from typing import Dict, Any, Optional, List

from app.utils.ai_clients.paraformer_client import ParaformerClient
from app.core.protocols.audio_protocols import ISpeechRecognitionService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ParaformerSpeechAdapter:
    """
    Paraformer语音识别适配器 (OCP: 开闭原则)
    适配器模式 - 让ParaformerClient实现ISpeechRecognitionService接口
    便于后续替换为其他ASR服务提供商（Whisper, Google STT等）
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化适配器

        Args:
            api_key: DashScope API密钥
        """
        self.client = ParaformerClient(api_key=api_key)
        logger.info("paraformer_speech_adapter_initialized")

    async def transcribe_from_url(
        self,
        audio_url: str,
        language_hints: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        从音频URL进行语音识别（适配接口）

        Args:
            audio_url: 音频文件URL
            language_hints: 语言提示

        Returns:
            转写结果字典
        """
        return await self.client.transcribe_audio(
            file_url=audio_url,
            language_hints=language_hints
        )

    def extract_text(self, transcription_data: Dict[str, Any]) -> str:
        """提取完整文本（适配接口）"""
        return self.client.extract_full_text(transcription_data)

    def format_for_llm(self, transcription_data: Dict[str, Any]) -> str:
        """格式化为LLM输入（适配接口）"""
        return self.client.format_transcript_for_llm(transcription_data)
