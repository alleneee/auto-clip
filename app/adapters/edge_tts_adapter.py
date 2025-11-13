"""Edge TTS 适配器"""
from typing import Optional
import edge_tts

from app.utils.logger import get_logger
from app.config import settings

logger = get_logger(__name__)


class EdgeTTSAdapter:
    """基于微软 Edge TTS 服务的适配器"""

    def __init__(
        self,
        default_voice: Optional[str] = None,
        default_rate: Optional[str] = None,
        default_pitch: Optional[str] = None,
        default_volume: Optional[str] = None
    ):
        self.default_voice = default_voice or settings.EDGE_TTS_VOICE
        self.default_rate = default_rate or settings.EDGE_TTS_RATE
        self.default_pitch = default_pitch or settings.EDGE_TTS_PITCH
        self.default_volume = default_volume or settings.EDGE_TTS_VOLUME

    def _normalize_percent(self, value: Optional[float | str]) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        sign = '+' if value >= 0 else ''
        return f"{sign}{value}%"

    def _normalize_pitch(self, value: Optional[float | str]) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        sign = '+' if value >= 0 else ''
        return f"{sign}{value}Hz"

    async def synthesize_speech(
        self,
        text: str,
        voice: Optional[str] = None,
        output_format: str = "mp3",
        sample_rate: Optional[int] = None,
        rate: Optional[float | str] = None,
        pitch: Optional[float | str] = None,
        volume: Optional[int | float | str] = None,
        style: Optional[str] = None,
        style_degree: Optional[float] = None
    ) -> bytes:
        kwargs = {
            "text": text,
            "voice": voice or self.default_voice,
            "rate": self._normalize_percent(rate) or self.default_rate,
            "pitch": self._normalize_pitch(pitch) or self.default_pitch,
            "volume": self._normalize_percent(volume) or self.default_volume,
        }
        if style:
            kwargs["style"] = style
        if style_degree is not None:
            kwargs["style_degree"] = style_degree
        communicator = edge_tts.Communicate(**kwargs)

        audio_buffer = bytearray()
        async for chunk in communicator.stream():
            if chunk["type"] == "audio":
                audio_buffer.extend(chunk["data"])

        return bytes(audio_buffer)

    async def synthesize_to_file(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None,
        output_format: str = "mp3",
        sample_rate: Optional[int] = None,
        rate: Optional[float | str] = None,
        pitch: Optional[float | str] = None,
        volume: Optional[int | float | str] = None,
        style: Optional[str] = None,
        style_degree: Optional[float] = None
    ) -> str:
        kwargs = {
            "text": text,
            "voice": voice or self.default_voice,
            "rate": self._normalize_percent(rate) or self.default_rate,
            "pitch": self._normalize_pitch(pitch) or self.default_pitch,
            "volume": self._normalize_percent(volume) or self.default_volume,
        }
        if style:
            kwargs["style"] = style
        if style_degree is not None:
            kwargs["style_degree"] = style_degree
        communicator = edge_tts.Communicate(**kwargs)

        await communicator.save(output_path)
        logger.info("edge_tts_audio_saved_to_file", output_path=output_path)
        return output_path
