"""
阿里云DashScope API客户端
支持qwen-vl-plus视觉分析和qwen-plus文本生成
"""
from typing import Optional, Dict, Any, List
import dashscope
from dashscope import MultiModalConversation

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
        self, video_path: str, prompt: Optional[str] = None
    ) -> str:
        """
        使用qwen-vl-plus分析视频视觉内容

        Args:
            video_path: 视频文件路径
            prompt: 自定义提示词

        Returns:
            视觉分析结果
        """
        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"video": f"file://{video_path}"},
                        {"text": prompt or VideoAnalysisPrompts.VISUAL_ANALYSIS_DEFAULT},
                    ],
                }
            ]

            logger.info(
                "calling_dashscope_vl",
                model=settings.DASHSCOPE_VL_MODEL,
                video=video_path,
            )

            response = MultiModalConversation.call(
                model=settings.DASHSCOPE_VL_MODEL, messages=messages
            )

            if response.status_code == 200:
                result = response.output.choices[0].message.content
                logger.info("dashscope_vl_success", video=video_path)
                return result
            else:
                error_msg = f"DashScope API错误: {response.message}"
                logger.error("dashscope_vl_failed", error=error_msg)
                raise LLMServiceError(error_msg)

        except Exception as e:
            logger.error("dashscope_vl_exception", error=str(e))
            raise LLMServiceError(f"视觉分析失败: {str(e)}")

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
