"""
Kokoro TTS 适配器

Kokoro是一个开源的82M参数TTS模型，支持8种语言：
- 'a': 美式英语
- 'b': 英式英语
- 'e': 西班牙语
- 'f': 法语
- 'h': 印地语
- 'i': 意大利语
- 'j': 日语
- 'p': 巴西葡萄牙语
- 'z': 中文

特点：
- 轻量级（82M参数）
- 快速推理
- 本地运行，无需API密钥
- Apache许可证
"""

from typing import Optional
from pathlib import Path
import asyncio
import io
import struct
import numpy as np

from app.utils.logger import get_logger
from app.config import settings

logger = get_logger(__name__)


# Kokoro语言代码映射
KOKORO_LANG_CODES = {
    "en-US": "a",  # 美式英语
    "en-GB": "b",  # 英式英语
    "es": "e",     # 西班牙语
    "fr": "f",     # 法语
    "hi": "h",     # 印地语
    "it": "i",     # 意大利语
    "ja": "j",     # 日语
    "pt-BR": "p",  # 巴西葡萄牙语
    "zh-CN": "z",  # 中文
    "zh": "z",     # 中文简写
}

# Kokoro音色列表（示例，实际可用音色需查看官方文档）
KOKORO_VOICES = {
    "a": ["af_heart", "af_sky", "am_adam", "am_michael"],  # 美式英语音色
    "z": ["af_xiaoxiao", "af_xiaomo", "am_xiaochen"],      # 中文音色（需要验证）
    # 其他语言音色可以根据实际支持情况添加
}


class KokoroTTSAdapter:
    """
    Kokoro TTS适配器

    本地运行的开源TTS模型，无需API密钥
    """

    def __init__(
        self,
        default_voice: Optional[str] = None,
        default_lang: str = "zh-CN",
        default_speed: float = 1.0,
        model_path: Optional[str] = None
    ):
        """
        初始化Kokoro TTS适配器

        Args:
            default_voice: 默认音色（如'af_heart'）
            default_lang: 默认语言（如'zh-CN'）
            default_speed: 默认语速（0.5-2.0）
            model_path: 模型路径（可选，默认自动下载）
        """
        self.default_voice = default_voice or getattr(settings, "KOKORO_VOICE", "af_heart")
        self.default_lang = default_lang
        self.default_speed = default_speed
        self.model_path = model_path

        # 延迟加载（只有在首次使用时才导入和初始化）
        self._pipeline = None
        self._current_lang = None

        logger.info(
            "kokoro_tts_adapter_initialized",
            default_voice=self.default_voice,
            default_lang=self.default_lang,
            default_speed=self.default_speed
        )

    def _ensure_pipeline(self, lang_code: str):
        """
        确保Pipeline已初始化（懒加载）

        Args:
            lang_code: Kokoro语言代码（如'a', 'z'）
        """
        try:
            from kokoro import KPipeline
        except ImportError:
            raise ImportError(
                "Kokoro TTS未安装。请运行: pip install kokoro>=0.9.4 soundfile\n"
                "Linux/Mac还需要: apt-get install espeak-ng 或 brew install espeak"
            )

        # 如果语言改变或Pipeline未初始化，重新创建
        if self._pipeline is None or self._current_lang != lang_code:
            logger.info(
                "initializing_kokoro_pipeline",
                lang_code=lang_code,
                model_path=self.model_path
            )

            # 初始化参数
            init_kwargs = {"lang_code": lang_code}
            if self.model_path:
                init_kwargs["model_path"] = self.model_path

            self._pipeline = KPipeline(**init_kwargs)
            self._current_lang = lang_code

            logger.info("kokoro_pipeline_ready", lang_code=lang_code)

    def _normalize_lang_code(self, lang: Optional[str] = None) -> str:
        """
        将标准语言代码转换为Kokoro语言代码

        Args:
            lang: 标准语言代码（如'zh-CN', 'en-US'）

        Returns:
            Kokoro语言代码（如'z', 'a'）
        """
        lang = lang or self.default_lang
        kokoro_code = KOKORO_LANG_CODES.get(lang)

        if kokoro_code is None:
            logger.warning(
                "unsupported_language_fallback_to_english",
                requested_lang=lang,
                fallback="a"
            )
            kokoro_code = "a"  # 默认美式英语

        return kokoro_code

    def _audio_to_wav_bytes(self, audio_data: np.ndarray, sample_rate: int = 24000) -> bytes:
        """
        将音频数组转换为WAV格式字节流

        Args:
            audio_data: 音频数组（float32）
            sample_rate: 采样率（Kokoro默认24kHz）

        Returns:
            WAV格式音频字节流
        """
        # 确保音频是float32格式
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        # 归一化到[-1, 1]范围
        if audio_data.max() > 1.0 or audio_data.min() < -1.0:
            audio_data = audio_data / max(abs(audio_data.max()), abs(audio_data.min()))

        # 转换为16位PCM
        pcm_data = (audio_data * 32767).astype(np.int16)

        # 构建WAV文件头
        buffer = io.BytesIO()

        # RIFF头
        buffer.write(b'RIFF')
        buffer.write(struct.pack('<I', 36 + len(pcm_data) * 2))  # 文件大小
        buffer.write(b'WAVE')

        # fmt子块
        buffer.write(b'fmt ')
        buffer.write(struct.pack('<I', 16))  # fmt块大小
        buffer.write(struct.pack('<H', 1))   # 音频格式（1=PCM）
        buffer.write(struct.pack('<H', 1))   # 声道数（1=单声道）
        buffer.write(struct.pack('<I', sample_rate))  # 采样率
        buffer.write(struct.pack('<I', sample_rate * 2))  # 字节率
        buffer.write(struct.pack('<H', 2))   # 块对齐
        buffer.write(struct.pack('<H', 16))  # 位深度

        # data子块
        buffer.write(b'data')
        buffer.write(struct.pack('<I', len(pcm_data) * 2))
        buffer.write(pcm_data.tobytes())

        return buffer.getvalue()

    async def synthesize_speech(
        self,
        text: str,
        voice: Optional[str] = None,
        output_format: str = "wav",
        sample_rate: Optional[int] = None,  # noqa: ARG002 - 接口兼容性
        speed: Optional[float] = None,
        lang: Optional[str] = None,
        **kwargs  # noqa: ARG002 - 接口兼容性
    ) -> bytes:
        """
        将文本转换为语音

        Args:
            text: 要转换的文本
            voice: 音色（如'af_heart'）
            output_format: 输出格式（目前仅支持'wav'）
            sample_rate: 采样率（Kokoro固定24kHz）
            speed: 语速（0.5-2.0）
            lang: 语言代码（如'zh-CN', 'en-US'）
            **kwargs: 其他参数

        Returns:
            音频数据(bytes)
        """
        if output_format not in ["wav", "mp3"]:
            logger.warning(
                "kokoro_only_supports_wav_converting_to_mp3",
                requested_format=output_format
            )

        # 标准化参数
        lang_code = self._normalize_lang_code(lang)
        voice = voice or self.default_voice
        speed = speed or self.default_speed

        # 确保Pipeline已初始化
        self._ensure_pipeline(lang_code)

        logger.info(
            "kokoro_synthesizing_speech",
            text_length=len(text),
            voice=voice,
            speed=speed,
            lang_code=lang_code
        )

        # 运行在单独的线程（Kokoro是同步的）
        def _generate_audio():
            # 生成音频
            generator = self._pipeline(text, voice=voice, speed=speed)

            # 收集所有音频片段
            audio_segments = []
            for _, _, audio_chunk in generator:  # graphemes和phonemes暂不使用
                audio_segments.append(audio_chunk)

            # 合并音频
            if audio_segments:
                full_audio = np.concatenate(audio_segments)
            else:
                # 空音频
                full_audio = np.zeros(0, dtype=np.float32)

            return full_audio

        # 异步运行
        loop = asyncio.get_event_loop()
        audio_array = await loop.run_in_executor(None, _generate_audio)

        # 转换为WAV格式
        wav_bytes = self._audio_to_wav_bytes(audio_array, sample_rate=24000)

        # 如果需要MP3格式，进行转换
        if output_format == "mp3":
            try:
                from pydub import AudioSegment
                audio_segment = AudioSegment.from_wav(io.BytesIO(wav_bytes))
                mp3_buffer = io.BytesIO()
                audio_segment.export(mp3_buffer, format="mp3")
                result_bytes = mp3_buffer.getvalue()
                logger.info("kokoro_audio_converted_to_mp3")
            except ImportError:
                logger.warning(
                    "pydub_not_installed_returning_wav",
                    hint="pip install pydub"
                )
                result_bytes = wav_bytes
        else:
            result_bytes = wav_bytes

        logger.info(
            "kokoro_synthesis_completed",
            audio_size_kb=len(result_bytes) / 1024
        )

        return result_bytes

    async def synthesize_to_file(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None,
        output_format: str = "wav",
        sample_rate: Optional[int] = None,
        speed: Optional[float] = None,
        lang: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        将文本转换为语音并保存到文件

        Args:
            text: 要转换的文本
            output_path: 输出文件路径
            voice: 音色
            output_format: 输出格式
            sample_rate: 采样率
            speed: 语速
            lang: 语言代码
            **kwargs: 其他参数

        Returns:
            保存的文件路径
        """
        # 从文件路径推断输出格式
        output_path_obj = Path(output_path)
        inferred_format = output_path_obj.suffix.lstrip('.')
        if inferred_format:
            output_format = inferred_format

        # 生成音频
        audio_data = await self.synthesize_speech(
            text=text,
            voice=voice,
            output_format=output_format,
            sample_rate=sample_rate,
            speed=speed,
            lang=lang,
            **kwargs
        )

        # 异步写入文件
        import aiofiles
        async with aiofiles.open(output_path, 'wb') as f:
            await f.write(audio_data)

        logger.info("kokoro_audio_saved_to_file", output_path=output_path)
        return output_path
