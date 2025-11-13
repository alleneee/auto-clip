"""
Google Gemini API客户端
支持自定义base_url的视频理解分析
"""
from typing import Optional, Dict, Any
import httpx
import base64
from pathlib import Path

from app.config import settings
from app.core.exceptions import LLMServiceError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class GeminiClient:
    """
    Google Gemini API客户端

    支持：
    - 自定义base_url（用于代理或镜像服务）
    - gemini-2.0-flash-exp视频理解
    - 本地视频文件和URL两种方式
    - 灵活的API配置
    """

    # 默认配置
    DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
    DEFAULT_MODEL = "gemini-2.0-flash-exp"
    DEFAULT_TIMEOUT = 120.0  # 视频分析可能需要较长时间

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT
    ):
        """
        初始化Gemini客户端

        Args:
            api_key: Gemini API密钥（默认从配置读取）
            base_url: API基础URL（支持自定义代理地址）
            model: 模型名称（默认gemini-2.0-flash-exp）
            timeout: 请求超时时间（秒）
        """
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.base_url = (base_url or settings.GEMINI_BASE_URL or self.DEFAULT_BASE_URL).rstrip('/')
        self.model = model or settings.GEMINI_MODEL or self.DEFAULT_MODEL
        self.timeout = timeout

        if not self.api_key:
            raise ValueError("Gemini API密钥未配置，请设置GEMINI_API_KEY环境变量")

        logger.info(
            "gemini_client_initialized",
            model=self.model,
            base_url=self.base_url,
            timeout=self.timeout
        )

    def _build_endpoint(self, method: str = "generateContent") -> str:
        """
        构建API端点URL

        Args:
            method: API方法（generateContent, streamGenerateContent等）

        Returns:
            完整的API端点URL
        """
        return f"{self.base_url}/models/{self.model}:{method}"

    async def analyze_video_from_path(
        self,
        video_path: str,
        prompt: str,
        max_output_tokens: int = 4096,
        temperature: float = 0.7
    ) -> str:
        """
        从本地路径分析视频（使用base64编码）

        Args:
            video_path: 本地视频文件路径
            prompt: 分析提示词
            max_output_tokens: 最大输出token数
            temperature: 温度参数（0-1）

        Returns:
            视频分析结果文本

        Raises:
            FileNotFoundError: 视频文件不存在
            LLMServiceError: API调用失败
        """
        path = Path(video_path)
        if not path.exists():
            raise FileNotFoundError(f"视频文件不存在：{video_path}")

        # 读取并编码视频
        with open(path, "rb") as f:
            video_data = base64.b64encode(f.read()).decode("utf-8")

        logger.info(
            "encoding_video_for_gemini",
            video_path=video_path,
            size_kb=len(video_data) / 1024,
            model=self.model
        )

        return await self._call_api(
            video_data=video_data,
            mime_type=self._get_mime_type(path),
            prompt=prompt,
            max_output_tokens=max_output_tokens,
            temperature=temperature
        )

    async def analyze_video_from_base64(
        self,
        video_base64: str,
        prompt: str,
        mime_type: str = "video/mp4",
        max_output_tokens: int = 4096,
        temperature: float = 0.7
    ) -> str:
        """
        从base64编码分析视频

        Args:
            video_base64: base64编码的视频数据（不含data URI前缀）
            prompt: 分析提示词
            mime_type: 视频MIME类型
            max_output_tokens: 最大输出token数
            temperature: 温度参数

        Returns:
            视频分析结果文本
        """
        logger.info(
            "analyzing_video_from_base64",
            base64_size_kb=len(video_base64) / 1024,
            mime_type=mime_type,
            model=self.model
        )

        return await self._call_api(
            video_data=video_base64,
            mime_type=mime_type,
            prompt=prompt,
            max_output_tokens=max_output_tokens,
            temperature=temperature
        )

    async def _call_api(
        self,
        video_data: str,
        mime_type: str,
        prompt: str,
        max_output_tokens: int,
        temperature: float
    ) -> str:
        """
        调用Gemini API

        Args:
            video_data: base64编码的视频数据
            mime_type: 视频MIME类型
            prompt: 分析提示词
            max_output_tokens: 最大输出token数
            temperature: 温度参数

        Returns:
            API返回的分析结果

        Raises:
            LLMServiceError: API调用失败
        """
        endpoint = self._build_endpoint("generateContent")
        url = f"{endpoint}?key={self.api_key}"

        # 构建请求体（Gemini API格式）
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": video_data
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "maxOutputTokens": max_output_tokens,
                "temperature": temperature
            }
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(
                    "calling_gemini_api",
                    model=self.model,
                    base_url=self.base_url,
                    prompt_length=len(prompt)
                )

                response = await client.post(url, json=payload)
                response.raise_for_status()

                result = response.json()

                # 提取响应内容
                if "candidates" in result and len(result["candidates"]) > 0:
                    candidate = result["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        parts = candidate["content"]["parts"]
                        if len(parts) > 0 and "text" in parts[0]:
                            analysis_result = parts[0]["text"]

                            logger.info(
                                "gemini_api_success",
                                model=self.model,
                                response_length=len(analysis_result),
                                usage=result.get("usageMetadata")
                            )

                            return analysis_result

                # 响应格式不符合预期
                error_msg = f"Gemini API响应格式异常: {result}"
                logger.error("gemini_api_unexpected_response", response=result)
                raise LLMServiceError(error_msg)

        except httpx.HTTPStatusError as e:
            error_msg = f"Gemini API HTTP错误 ({e.response.status_code}): {e.response.text}"
            logger.error(
                "gemini_api_http_error",
                status_code=e.response.status_code,
                error=e.response.text
            )
            raise LLMServiceError(error_msg)

        except httpx.TimeoutException:
            error_msg = f"Gemini API请求超时（>{self.timeout}秒）"
            logger.error("gemini_api_timeout", timeout=self.timeout)
            raise LLMServiceError(error_msg)

        except Exception as e:
            error_msg = f"Gemini API调用失败: {str(e)}"
            logger.error("gemini_api_exception", error=str(e), error_type=type(e).__name__)
            raise LLMServiceError(error_msg)

    def _get_mime_type(self, path: Path) -> str:
        """
        根据文件扩展名获取MIME类型

        Args:
            path: 文件路径

        Returns:
            MIME类型字符串
        """
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
        return mime_map.get(suffix, "video/mp4")  # 默认mp4

    async def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_output_tokens: int = 2048,
        temperature: float = 0.7
    ) -> str:
        """
        纯文本对话（不含视频）

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词（Gemini通过特殊格式支持）
            max_output_tokens: 最大输出token数
            temperature: 温度参数

        Returns:
            AI回复文本
        """
        endpoint = self._build_endpoint("generateContent")
        url = f"{endpoint}?key={self.api_key}"

        # 构建消息内容
        content_parts = []
        if system_prompt:
            content_parts.append({"text": f"[System]: {system_prompt}\n\n{prompt}"})
        else:
            content_parts.append({"text": prompt})

        payload = {
            "contents": [{"parts": content_parts}],
            "generationConfig": {
                "maxOutputTokens": max_output_tokens,
                "temperature": temperature
            }
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(
                    "calling_gemini_chat",
                    model=self.model,
                    prompt_length=len(prompt)
                )

                response = await client.post(url, json=payload)
                response.raise_for_status()

                result = response.json()

                if "candidates" in result and len(result["candidates"]) > 0:
                    candidate = result["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        parts = candidate["content"]["parts"]
                        if len(parts) > 0 and "text" in parts[0]:
                            reply = parts[0]["text"]

                            logger.info(
                                "gemini_chat_success",
                                response_length=len(reply)
                            )

                            return reply

                error_msg = f"Gemini API响应格式异常: {result}"
                logger.error("gemini_chat_unexpected_response", response=result)
                raise LLMServiceError(error_msg)

        except Exception as e:
            logger.error("gemini_chat_exception", error=str(e))
            raise LLMServiceError(f"Gemini对话失败: {str(e)}")
