"""
LiteLLM多模态工具

统一接口调用多种大模型（Gemini、GPT-4o、Claude、DashScope等）进行视频分析
"""

import os
import base64
from pathlib import Path
from typing import Optional, List, Dict, Any
import litellm
from litellm import completion
import structlog

logger = structlog.get_logger(__name__)


class LiteLLMMultimodalTool:
    """
    LiteLLM多模态分析工具

    支持的模型：
    - gemini/gemini-2.0-flash-exp (推荐，原生视频支持)
    - gpt-4o (OpenAI视频支持)
    - claude-3-5-sonnet (Anthropic多模态)
    - dashscope/qwen-vl-plus (阿里云视觉模型)
    """

    # 默认模型配置
    DEFAULT_MODEL = "gemini/gemini-2.0-flash-exp"

    # 支持的视频格式
    SUPPORTED_VIDEO_FORMATS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        api_key: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ):
        """
        初始化多模态工具

        Args:
            model: 模型名称（如"gemini/gemini-2.0-flash-exp"）
            api_key: API密钥（可选，优先级：参数 > 环境变量）
            max_tokens: 最大生成token数
            temperature: 温度参数
        """
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

        # API密钥处理
        self._setup_api_keys(api_key)

        # 启用详细日志（开发阶段）
        litellm.set_verbose = False  # 生产环境设为False

        logger.info(
            "LiteLLM多模态工具初始化",
            model=self.model,
            max_tokens=self.max_tokens
        )

    def _setup_api_keys(self, api_key: Optional[str] = None):
        """
        设置API密钥

        优先级：参数 > 环境变量
        """
        if api_key:
            # 根据模型类型设置对应的环境变量
            if self.model.startswith("gemini"):
                os.environ["GEMINI_API_KEY"] = api_key
            elif self.model.startswith("gpt"):
                os.environ["OPENAI_API_KEY"] = api_key
            elif self.model.startswith("claude"):
                os.environ["ANTHROPIC_API_KEY"] = api_key
            elif self.model.startswith("dashscope"):
                os.environ["DASHSCOPE_API_KEY"] = api_key

        # 验证必要的环境变量是否存在
        required_key = self._get_required_env_key()
        if required_key and not os.getenv(required_key):
            logger.warning(
                f"未设置{required_key}环境变量，可能导致API调用失败",
                model=self.model
            )

    def _get_required_env_key(self) -> Optional[str]:
        """获取模型所需的环境变量名"""
        if self.model.startswith("gemini"):
            return "GEMINI_API_KEY"
        elif self.model.startswith("gpt"):
            return "OPENAI_API_KEY"
        elif self.model.startswith("claude"):
            return "ANTHROPIC_API_KEY"
        elif self.model.startswith("dashscope"):
            return "DASHSCOPE_API_KEY"
        return None

    def _validate_video_path(self, video_path: str) -> Path:
        """验证视频路径"""
        path = Path(video_path)

        if not path.exists():
            raise FileNotFoundError(f"视频文件不存在：{video_path}")

        if path.suffix.lower() not in self.SUPPORTED_VIDEO_FORMATS:
            raise ValueError(
                f"不支持的视频格式：{path.suffix}。"
                f"支持的格式：{', '.join(self.SUPPORTED_VIDEO_FORMATS)}"
            )

        return path

    def _encode_video_for_api(self, video_path: Path) -> Dict[str, Any]:
        """
        为不同模型准备视频输入格式

        Returns:
            适合LiteLLM的content格式
        """
        # Gemini 2.0原生支持视频文件路径
        if self.model.startswith("gemini"):
            return {
                "type": "video_url",
                "video_url": {"url": f"file://{video_path.absolute()}"}
            }

        # GPT-4o需要base64编码（仅支持短视频）
        elif self.model.startswith("gpt"):
            with open(video_path, "rb") as f:
                video_data = base64.b64encode(f.read()).decode("utf-8")
            return {
                "type": "video_url",
                "video_url": {"url": f"data:video/mp4;base64,{video_data}"}
            }

        # Claude和其他模型（降级为图像帧）
        else:
            logger.warning(
                f"模型{self.model}不原生支持视频，建议使用Gemini或GPT-4o"
            )
            # TODO: 实现视频帧提取逻辑
            raise NotImplementedError(f"模型{self.model}的视频支持尚未实现")

    async def analyze_video(
        self,
        video_path: str,
        prompt: str,
        response_format: Optional[str] = "json"
    ) -> Dict[str, Any]:
        """
        分析视频内容

        Args:
            video_path: 视频文件路径
            prompt: 分析提示词
            response_format: 返回格式（"json"或"text"）

        Returns:
            模型返回的分析结果
        """
        # 验证路径
        path = self._validate_video_path(video_path)

        # 准备视频内容
        video_content = self._encode_video_for_api(path)

        # 构建消息
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    video_content
                ]
            }
        ]

        logger.info(
            "开始视频分析",
            video_path=str(path),
            model=self.model,
            prompt_length=len(prompt)
        )

        try:
            # 调用LiteLLM
            response = await completion(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                response_format={"type": response_format} if response_format == "json" else None
            )

            # 提取结果
            content = response.choices[0].message.content

            logger.info(
                "视频分析完成",
                model=self.model,
                response_length=len(content),
                usage=response.usage.dict() if response.usage else None
            )

            return {
                "content": content,
                "model": response.model,
                "usage": response.usage.dict() if response.usage else None
            }

        except Exception as e:
            logger.error(
                "视频分析失败",
                model=self.model,
                error=str(e),
                video_path=str(path)
            )
            raise

    def analyze_video_sync(
        self,
        video_path: str,
        prompt: str,
        response_format: Optional[str] = "json"
    ) -> Dict[str, Any]:
        """
        同步方式分析视频（用于非异步环境）

        Args:
            video_path: 视频文件路径
            prompt: 分析提示词
            response_format: 返回格式（"json"或"text"）

        Returns:
            模型返回的分析结果
        """
        # 验证路径
        path = self._validate_video_path(video_path)

        # 准备视频内容
        video_content = self._encode_video_for_api(path)

        # 构建消息
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    video_content
                ]
            }
        ]

        logger.info(
            "开始视频分析（同步）",
            video_path=str(path),
            model=self.model
        )

        try:
            # 同步调用
            response = completion(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                response_format={"type": response_format} if response_format == "json" else None
            )

            content = response.choices[0].message.content

            logger.info(
                "视频分析完成（同步）",
                model=self.model,
                response_length=len(content)
            )

            return {
                "content": content,
                "model": response.model,
                "usage": response.usage.dict() if response.usage else None
            }

        except Exception as e:
            logger.error(
                "视频分析失败（同步）",
                model=self.model,
                error=str(e)
            )
            raise


# 导出便捷函数
def create_multimodal_tool(
    model: str = LiteLLMMultimodalTool.DEFAULT_MODEL,
    **kwargs
) -> LiteLLMMultimodalTool:
    """
    创建多模态工具的便捷函数

    Args:
        model: 模型名称
        **kwargs: 其他参数

    Returns:
        LiteLLMMultimodalTool实例
    """
    return LiteLLMMultimodalTool(model=model, **kwargs)
