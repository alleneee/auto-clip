"""
阿里云DashScope API客户端
支持qwen-vl-plus视觉分析、qwen-plus文本生成和CosyVoice语音合成
"""
from typing import Optional, Dict, Any, List
import dashscope
from dashscope import MultiModalConversation, Generation, audio

from app.config import settings
from app.core.exceptions import LLMServiceError
from app.utils.logger import get_logger
from app.prompts import VideoAnalysisPrompts, ThemeGenerationPrompts

logger = get_logger(__name__)


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
        voice: str = "Cherry",  # qwen3-tts-flash默认音色
        output_format: str = "mp3",
        sample_rate: int = 22050
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
            logger.info(
                "calling_dashscope_tts",
                voice=voice,
                text_length=len(text),
                format=output_format
            )

            # 调用Qwen TTS API (根据官方示例)
            response = audio.qwen_tts.SpeechSynthesizer.call(
                model='qwen3-tts-flash',  # 使用qwen3-tts-flash模型
                api_key=self.api_key,
                text=text,
                voice=voice
            )

            if response.status_code == 200:
                # 获取音频URL并下载
                audio_url = response.output['audio']['url']

                logger.info(
                    "dashscope_tts_downloading",
                    url=audio_url[:100] + "..." if len(audio_url) > 100 else audio_url
                )

                # 下载音频数据
                import requests
                audio_response = requests.get(audio_url, timeout=30)
                audio_response.raise_for_status()
                audio_data = audio_response.content

                logger.info(
                    "dashscope_tts_success",
                    audio_size_kb=len(audio_data) / 1024
                )
                return audio_data
            else:
                error_msg = f"DashScope TTS API错误: {response.message}"
                logger.error("dashscope_tts_failed", error=error_msg)
                raise LLMServiceError(error_msg)

        except Exception as e:
            logger.error("dashscope_tts_exception", error=str(e))
            raise LLMServiceError(f"语音合成失败: {str(e)}")
