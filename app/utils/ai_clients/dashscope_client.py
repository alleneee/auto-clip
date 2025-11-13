"""
阿里云DashScope API客户端
支持qwen-vl-plus视觉分析、qwen-plus文本生成和CosyVoice语音合成
"""
import asyncio
from functools import partial
from typing import Optional, Dict, Any, List
import dashscope
from dashscope import MultiModalConversation, Generation
from dashscope.audio.tts import SpeechSynthesizer
from dashscope.audio.tts import speech_synthesizer as _speech_module
from http import HTTPStatus
import requests

from app.config import settings
from app.core.exceptions import LLMServiceError
from app.utils.logger import get_logger
from app.prompts import VideoAnalysisPrompts, ThemeGenerationPrompts

logger = get_logger(__name__)


_SPEECH_SYNTH_PATCHED = False


def _ensure_speech_synth_patch():
    global _SPEECH_SYNTH_PATCHED
    if _SPEECH_SYNTH_PATCHED:
        return

    # 复制官方实现，增加对缺失字段的容错处理
    original_class = SpeechSynthesizer

    @classmethod
    def _patched_call(cls, model: str, text: str, callback=None, **kwargs):
        _callback = callback
        _audio_data: bytes = None
        _sentences: List[Dict[str, Any]] = []
        _the_final_response = None
        _task_failed_flag: bool = False
        task_name, _ = _speech_module._get_task_group_and_task(_speech_module.__name__)

        response = super(SpeechSynthesizer, cls).call(
            model=model,
            task_group='audio',
            task=task_name,
            function='SpeechSynthesizer',
            input={'text': text},
            stream=True,
            api_protocol=_speech_module.ApiProtocol.WEBSOCKET,
            **kwargs
        )

        if _callback is not None:
            _callback.on_open()

        for part in response:
            if isinstance(part.output, bytes):
                if _callback is not None:
                    audio_frame = _speech_module.SpeechSynthesisResult(
                        bytes(part.output), None, None, None, None
                    )
                    _callback.on_event(audio_frame)

                if _audio_data is None:
                    _audio_data = bytes(part.output)
                else:
                    _audio_data = _audio_data + bytes(part.output)

            else:
                if part.status_code == HTTPStatus.OK:
                    if part.output is None:
                        _the_final_response = _speech_module.SpeechSynthesisResponse.from_api_response(part)
                    else:
                        sentence = part.output.get('sentence') if isinstance(part.output, dict) else None
                        if sentence:
                            if _callback is not None:
                                sentence_result = _speech_module.SpeechSynthesisResult(
                                    None, None, sentence, None, None
                                )
                                _callback.on_event(sentence_result)

                            prev = _sentences[-1] if _sentences else None
                            begin = sentence.get('begin_time') or sentence.get('beginTime')
                            end = sentence.get('end_time') or sentence.get('endTime')
                            if prev and begin is not None and prev.get('begin_time', prev.get('beginTime')) == begin:
                                prev_end = prev.get('end_time', prev.get('endTime'))
                                if end is not None and prev_end != end:
                                    _sentences.pop()
                                    _sentences.append(sentence)
                            else:
                                _sentences.append(sentence)
                else:
                    _task_failed_flag = True
                    _the_final_response = _speech_module.SpeechSynthesisResponse.from_api_response(part)
                    if _callback is not None:
                        _callback.on_error(
                            _speech_module.SpeechSynthesisResponse.from_api_response(part)
                        )

        if _callback is not None:
            if not _task_failed_flag:
                _callback.on_complete()
            _callback.on_close()

        result = _speech_module.SpeechSynthesisResult(None, _audio_data, None, _sentences, _the_final_response)
        return result

    original_class.call = _patched_call
    _SPEECH_SYNTH_PATCHED = True


class DashScopeClient:
    """DashScope API客户端"""

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化客户端

        Args:
            api_key: API密钥，默认从配置读取
        """
        self.api_key = api_key or settings.DASHSCOPE_API_KEY
        dashscope.api_key = self.api_key
        self.tts_model = settings.DASHSCOPE_TTS_MODEL
        _ensure_speech_synth_patch()

    async def analyze_video_visual(
        self, video_url: str, prompt: Optional[str] = None
    ) -> str:
        """
        使用qwen-vl-plus分析视频视觉内容（仅支持网络URL）

        Args:
            video_url: 视频的网络地址（HTTP/HTTPS URL）
            prompt: 自定义提示词

        Returns:
            视觉分析结果

        Note:
            此方法仅支持公网可访问的视频URL（如OSS签名URL）
            本地文件请使用 analyze_video_visual_base64 方法
        """
        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"video": video_url},
                        {"text": prompt or VideoAnalysisPrompts.VISUAL_ANALYSIS_DEFAULT},
                    ],
                }
            ]

            logger.info(
                "calling_dashscope_vl_url",
                model=settings.DASHSCOPE_VL_MODEL,
                video_url=video_url[:100] + "..." if len(video_url) > 100 else video_url
            )

            response = MultiModalConversation.call(
                model=settings.DASHSCOPE_VL_MODEL, messages=messages
            )

            if response.status_code == 200:
                result = response.output.choices[0].message.content[0]["text"]
                logger.info("dashscope_vl_url_success")
                return result
            else:
                error_msg = f"DashScope API错误: {response.message}"
                logger.error("dashscope_vl_url_failed", error=error_msg)
                raise LLMServiceError(error_msg)

        except Exception as e:
            logger.error("dashscope_vl_url_exception", error=str(e))
            raise LLMServiceError(f"视觉分析失败（URL方式）: {str(e)}")

    async def analyze_video_visual_base64(
        self,
        video_base64: str,
        prompt: Optional[str] = None
    ) -> str:
        """
        使用qwen-vl-plus分析视频视觉内容（base64编码方式）

        Args:
            video_base64: 视频的base64编码字符串（不包含data URI前缀）
            prompt: 自定义提示词

        Returns:
            视觉分析结果

        Note:
            推荐用于预处理后的压缩视频临时文件
            视频会以 data:video/mp4;base64,{base64} 格式传递给API
        """
        try:
            # 构建base64 data URI
            video_data_uri = f"data:video/mp4;base64,{video_base64}"

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"video": video_data_uri},
                        {"text": prompt or VideoAnalysisPrompts.VISUAL_ANALYSIS_DEFAULT},
                    ],
                }
            ]

            logger.info(
                "calling_dashscope_vl_base64",
                model=settings.DASHSCOPE_VL_MODEL,
                base64_size_kb=len(video_base64) / 1024
            )

            response = MultiModalConversation.call(
                model=settings.DASHSCOPE_VL_MODEL, messages=messages
            )

            if response.status_code == 200:
                result = response.output.choices[0].message.content[0]["text"]
                logger.info("dashscope_vl_base64_success")
                return result
            else:
                error_msg = f"DashScope API错误: {response.message}"
                logger.error("dashscope_vl_base64_failed", error=error_msg)
                raise LLMServiceError(error_msg)

        except Exception as e:
            logger.error("dashscope_vl_base64_exception", error=str(e))
            raise LLMServiceError(f"视觉分析失败（base64方式）: {str(e)}")

    async def chat(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> str:
        """
        使用qwen-plus进行文本对话

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词

        Returns:
            AI回复
        """
        from dashscope import Generation

        try:
            messages = []

            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            messages.append({"role": "user", "content": prompt})

            logger.info(
                "calling_dashscope_chat", model=settings.DASHSCOPE_TEXT_MODEL
            )

            response = Generation.call(
                model=settings.DASHSCOPE_TEXT_MODEL,
                messages=messages,
                result_format="message",
            )

            if response.status_code == 200:
                result = response.output.choices[0].message.content
                logger.info("dashscope_chat_success")
                return result
            else:
                error_msg = f"DashScope API错误: {response.message}"
                logger.error("dashscope_chat_failed", error=error_msg)
                raise LLMServiceError(error_msg)

        except Exception as e:
            logger.error("dashscope_chat_exception", error=str(e))
            raise LLMServiceError(f"文本生成失败: {str(e)}")

    async def generate_theme(self, analyses: List[Dict[str, Any]]) -> str:
        """
        基于多个视频分析生成主题

        Args:
            analyses: 视频分析结果列表

        Returns:
            生成的主题
        """
        # 使用提示词模块生成提示词
        prompt = ThemeGenerationPrompts.generate_theme_prompt(analyses)
        system_prompt = ThemeGenerationPrompts.THEME_GENERATION_SYSTEM

        return await self.chat(prompt, system_prompt=system_prompt)

    async def synthesize_speech(
        self,
        text: str,
        voice: str = "Cherry",
        output_format: str = "mp3",
        sample_rate: Optional[int] = None,
        rate: Optional[float] = None,
        pitch: Optional[float] = None,
        volume: Optional[int] = None,
        model: Optional[str] = None,
        **_: Any
    ) -> bytes:
        """
        使用Qwen TTS将文本转换为语音

        Args:
            text: 要转换的文本
            voice: 音色选择 (Cherry/Peach/Plum等)
            output_format: 输出格式 (仅供兼容性，实际由API决定)
            sample_rate: 采样率 (仅供兼容性，实际由API决定)

        Returns:
            音频数据(bytes)

        Raises:
            LLMServiceError: TTS服务调用失败

        Note:
            使用qwen3-tts-flash模型
            支持的音色示例: Cherry, Peach, Plum等
            详细音色列表请参考DashScope文档
        """
        try:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                None,
                partial(
                    self._synthesize_speech_blocking,
                    text,
                    voice,
                    output_format,
                    sample_rate,
                    rate,
                    pitch,
                    volume,
                    model or self.tts_model
                )
            )
        except Exception as e:
            logger.error("dashscope_tts_exception", error=str(e))
            raise LLMServiceError(f"语音合成失败: {str(e)}")

    def _synthesize_speech_blocking(
        self,
        text: str,
        voice: str,
        output_format: str,
        sample_rate: Optional[int],
        rate: Optional[float],
        pitch: Optional[float],
        volume: Optional[int],
        model: str
    ) -> bytes:
        """同步执行TTS（供线程池调用）"""
        logger.info(
            "calling_dashscope_tts",
            voice=voice,
            text_length=len(text),
            format=output_format
        )

        call_kwargs: Dict[str, Any] = {
            "model": model,
            "text": text,
            "voice": voice,
            "format": output_format
        }
        if sample_rate:
            call_kwargs["sample_rate"] = sample_rate
        if rate:
            call_kwargs["rate"] = rate
        if pitch:
            call_kwargs["pitch"] = pitch
        if volume is not None:
            call_kwargs["volume"] = volume

        response = SpeechSynthesizer.call(**call_kwargs)

        resp_meta = response.get_response()
        status_code = getattr(resp_meta, "status_code", HTTPStatus.OK)
        if status_code != HTTPStatus.OK:
            error_msg = f"DashScope TTS API错误: {getattr(resp_meta, 'message', '未知错误')}"
            logger.error("dashscope_tts_failed", error=error_msg)
            raise LLMServiceError(error_msg)

        # 官方文档：https://help.aliyun.com/zh/model-studio/cosyvoice-python-sdk
        # 建议优先使用 SDK 返回的 audio data，避免重复下载
        audio_data = response.get_audio_data()
        if not audio_data:
            audio_frames = response.get_audio_frame()
            if audio_frames:
                audio_data = b"".join(audio_frames)

        if not audio_data:
            audio_url = None
            output_obj = getattr(resp_meta, "output", None)
            if output_obj and getattr(output_obj, "audio", None):
                audio_url = getattr(output_obj.audio, "url", None)
            if not audio_url:
                raise LLMServiceError("语音合成失败: 未返回音频数据")
            logger.info(
                "dashscope_tts_downloading",
                url=audio_url[:100] + "..." if len(audio_url) > 100 else audio_url
            )
            audio_response = requests.get(audio_url, timeout=30)
            audio_response.raise_for_status()
            audio_data = audio_response.content

        logger.info(
            "dashscope_tts_success",
            audio_size_kb=len(audio_data) / 1024
        )
        return audio_data
