"""
Gemini OpenAI兼容客户端
支持通过OpenAI兼容的代理服务访问Gemini
"""
from typing import Optional
import httpx
import base64
from pathlib import Path

from app.config import settings
from app.core.exceptions import LLMServiceError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class GeminiOpenAICompatibleClient:
    """
    Gemini OpenAI兼容客户端

    支持通过OpenAI兼容的代理服务（如OneAPI、NewAPI等）访问Gemini
    使用OpenAI API格式，而不是Gemini原生格式
    """

    DEFAULT_TIMEOUT = 120.0

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT
    ):
        """
        初始化客户端

        Args:
            api_key: API密钥
            base_url: API基础URL（OpenAI兼容格式）
            model: 模型名称
            timeout: 请求超时时间（秒）
        """
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.base_url = (base_url or settings.GEMINI_BASE_URL).rstrip('/')
        self.model = model or settings.GEMINI_MODEL or "gemini-2.0-flash"
        self.timeout = timeout

        if not self.api_key:
            raise ValueError("API密钥未配置，请设置GEMINI_API_KEY环境变量")

        logger.info(
            "gemini_openai_compatible_client_initialized",
            model=self.model,
            base_url=self.base_url,
            timeout=self.timeout
        )

    async def analyze_video_from_path(
        self,
        video_path: str,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> str:
        """
        从本地路径分析视频

        Args:
            video_path: 本地视频文件路径
            prompt: 分析提示词
            max_tokens: 最大输出token数
            temperature: 温度参数

        Returns:
            视频分析结果文本
        """
        path = Path(video_path)
        if not path.exists():
            raise FileNotFoundError(f"视频文件不存在：{video_path}")

        # 读取并编码视频
        with open(path, "rb") as f:
            video_data = base64.b64encode(f.read()).decode("utf-8")

        logger.info(
            "encoding_video_for_gemini_openai",
            video_path=video_path,
            size_kb=len(video_data) / 1024,
            model=self.model
        )

        # 构建data URI
        mime_type = self._get_mime_type(path)
        video_url = f"data:{mime_type};base64,{video_data}"

        return await self._call_api(
            video_url=video_url,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature
        )

    async def analyze_video_from_base64(
        self,
        video_base64: str,
        prompt: str,
        mime_type: str = "video/mp4",
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> str:
        """
        从base64编码分析视频

        Args:
            video_base64: base64编码的视频数据
            prompt: 分析提示词
            mime_type: 视频MIME类型
            max_tokens: 最大输出token数
            temperature: 温度参数

        Returns:
            视频分析结果文本
        """
        logger.info(
            "analyzing_video_from_base64_openai",
            base64_size_kb=len(video_base64) / 1024,
            mime_type=mime_type,
            model=self.model
        )

        video_url = f"data:{mime_type};base64,{video_base64}"

        return await self._call_api(
            video_url=video_url,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature
        )

    async def _call_api(
        self,
        video_url: str,
        prompt: str,
        max_tokens: int,
        temperature: float
    ) -> str:
        """
        调用OpenAI兼容的API

        Args:
            video_url: data URI格式的视频URL
            prompt: 分析提示词
            max_tokens: 最大输出token数
            temperature: 温度参数

        Returns:
            API返回的分析结果
        """
        # 构建OpenAI格式的请求
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",  # OpenAI格式使用image_url
                            "image_url": {
                                "url": video_url
                            }
                        }
                    ]
                }
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(
                    "calling_gemini_openai_api",
                    model=self.model,
                    base_url=self.base_url,
                    prompt_length=len(prompt)
                )

                response = await client.post(
                    self.base_url,
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()

                result = response.json()

                # 提取OpenAI格式的响应
                if "choices" in result and len(result["choices"]) > 0:
                    choice = result["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        content = choice["message"]["content"]

                        logger.info(
                            "gemini_openai_api_success",
                            model=self.model,
                            response_length=len(content),
                            usage=result.get("usage")
                        )

                        return content

                # 响应格式不符合预期
                error_msg = f"API响应格式异常: {result}"
                logger.error("gemini_openai_api_unexpected_response", response=result)
                raise LLMServiceError(error_msg)

        except httpx.HTTPStatusError as e:
            error_msg = f"API HTTP错误 ({e.response.status_code}): {e.response.text}"
            logger.error(
                "gemini_openai_api_http_error",
                status_code=e.response.status_code,
                error=e.response.text
            )
            raise LLMServiceError(error_msg)

        except httpx.TimeoutException:
            error_msg = f"API请求超时（>{self.timeout}秒）"
            logger.error("gemini_openai_api_timeout", timeout=self.timeout)
            raise LLMServiceError(error_msg)

        except Exception as e:
            error_msg = f"API调用失败: {str(e)}"
            logger.error(
                "gemini_openai_api_exception",
                error=str(e),
                error_type=type(e).__name__
            )
            raise LLMServiceError(error_msg)

    async def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7
    ) -> str:
        """
        纯文本对话

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            max_tokens: 最大输出token数
            temperature: 温度参数

        Returns:
            AI回复文本
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(
                    "calling_gemini_openai_chat",
                    model=self.model,
                    prompt_length=len(prompt)
                )

                response = await client.post(
                    self.base_url,
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()

                result = response.json()

                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"]

                    logger.info(
                        "gemini_openai_chat_success",
                        response_length=len(content)
                    )

                    return content

                error_msg = f"API响应格式异常: {result}"
                logger.error("gemini_openai_chat_unexpected_response", response=result)
                raise LLMServiceError(error_msg)

        except Exception as e:
            logger.error("gemini_openai_chat_exception", error=str(e))
            raise LLMServiceError(f"对话失败: {str(e)}")

    def _get_mime_type(self, path: Path) -> str:
        """根据文件扩展名获取MIME类型"""
        mime_map = {
            ".mp4": "video/mp4",
            ".mov": "video/quicktime",
            ".avi": "video/x-msvideo",
            ".mkv": "video/x-matroska",
            ".webm": "video/webm",
            ".flv": "video/x-flv",
            ".wmv": "video/x-ms-wmv"
        }

        suffix = path.suffix.lower()
        return mime_map.get(suffix, "video/mp4")
