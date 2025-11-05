"""
音频语音识别服务抽象接口 (SOLID: 依赖倒置原则)
"""
from typing import Protocol, Dict, Any, Optional, List


class ISpeechRecognitionService(Protocol):
    """语音识别服务接口 (支持多种ASR服务提供商)"""

    async def transcribe_from_url(
        self,
        audio_url: str,
        language_hints: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        从音频URL进行语音识别

        Args:
            audio_url: 音频文件的公网URL
            language_hints: 语言提示列表

        Returns:
            包含转写文本和时间戳的字典
        """
        ...

    def extract_text(self, transcription_data: Dict[str, Any]) -> str:
        """提取完整文本"""
        ...

    def format_for_llm(self, transcription_data: Dict[str, Any]) -> str:
        """格式化为LLM输入"""
        ...
