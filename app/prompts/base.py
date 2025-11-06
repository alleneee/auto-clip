"""
基础提示词类
所有提示词的基类，提供统一的接口和功能
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import json
from datetime import datetime

from app.prompts.metadata import PromptMetadata, PromptVersion, ModelType, OutputFormat


class BasePrompt(ABC):
    """提示词基类"""

    def __init__(self, metadata: PromptMetadata):
        """
        初始化提示词

        Args:
            metadata: 提示词元数据
        """
        self.metadata = metadata
        self._versions: Dict[str, PromptVersion] = {}

    @abstractmethod
    def get_template(self, version: Optional[str] = None) -> str:
        """
        获取提示词模板

        Args:
            version: 版本号，如果为None则返回当前版本

        Returns:
            提示词模板字符串
        """
        pass

    def format_prompt(self, **kwargs) -> str:
        """
        格式化提示词

        Args:
            **kwargs: 提示词参数

        Returns:
            格式化后的提示词

        Raises:
            ValueError: 参数验证失败
        """
        # 验证参数
        is_valid, missing = self.metadata.validate_parameters(kwargs)
        if not is_valid:
            raise ValueError(f"缺少必需参数: {missing}")

        # 获取模板
        template = self.get_template()

        # 格式化
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"模板格式化失败: {e}")

    def validate_output(self, output: str) -> tuple[bool, Optional[Any]]:
        """
        验证LLM输出

        Args:
            output: LLM输出字符串

        Returns:
            (是否有效, 解析后的数据)
        """
        if self.metadata.output_format == OutputFormat.JSON:
            try:
                parsed = json.loads(output)
                return True, parsed
            except json.JSONDecodeError:
                return False, None

        elif self.metadata.output_format == OutputFormat.TEXT:
            return len(output.strip()) > 0, output.strip()

        elif self.metadata.output_format == OutputFormat.MARKDOWN:
            return len(output.strip()) > 0, output.strip()

        else:
            return True, output

    def add_version(self, version: PromptVersion):
        """添加版本"""
        self._versions[version.version] = version

    def get_version(self, version: str) -> Optional[PromptVersion]:
        """获取指定版本"""
        return self._versions.get(version)

    def list_versions(self) -> List[Dict[str, Any]]:
        """列出所有版本"""
        return [v.to_dict() for v in self._versions.values()]

    def deprecate_version(self, version: str):
        """废弃某个版本"""
        if version in self._versions:
            self._versions[version].deprecated = True

    def __repr__(self):
        return f"<{self.__class__.__name__}(name='{self.metadata.name}', version='{self.metadata.version}')>"


class VisionPrompt(BasePrompt):
    """视觉模型提示词（支持图片输入）"""

    def __init__(self, metadata: PromptMetadata):
        if metadata.model_type != ModelType.VISION:
            metadata.model_type = ModelType.VISION
        super().__init__(metadata)

    def format_with_images(
        self,
        images: List[str],
        **kwargs
    ) -> Dict[str, Any]:
        """
        格式化包含图片的提示词

        Args:
            images: 图片路径或base64编码列表
            **kwargs: 其他参数

        Returns:
            包含文本和图片的提示词字典
        """
        text_prompt = self.format_prompt(**kwargs)

        return {
            "text": text_prompt,
            "images": images,
            "model_type": "vision"
        }


class TextPrompt(BasePrompt):
    """纯文本模型提示词"""

    def __init__(self, metadata: PromptMetadata):
        if metadata.model_type != ModelType.TEXT:
            metadata.model_type = ModelType.TEXT
        super().__init__(metadata)


class MultimodalPrompt(BasePrompt):
    """多模态提示词（支持文本、图片、音频等）"""

    def __init__(self, metadata: PromptMetadata):
        if metadata.model_type != ModelType.MULTIMODAL:
            metadata.model_type = ModelType.MULTIMODAL
        super().__init__(metadata)

    def format_multimodal(
        self,
        text_params: Dict[str, Any],
        images: Optional[List[str]] = None,
        audio: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        格式化多模态提示词

        Args:
            text_params: 文本参数
            images: 图片列表
            audio: 音频列表
            **kwargs: 其他参数

        Returns:
            多模态提示词字典
        """
        text_prompt = self.format_prompt(**text_params, **kwargs)

        result = {
            "text": text_prompt,
            "model_type": "multimodal"
        }

        if images:
            result["images"] = images

        if audio:
            result["audio"] = audio

        return result


class PromptBuilder:
    """提示词构建器（辅助类）"""

    def __init__(self):
        self.sections = []

    def add_section(self, title: str, content: str):
        """添加一个章节"""
        self.sections.append(f"## {title}\n{content}")
        return self

    def add_list(self, title: str, items: List[str]):
        """添加列表"""
        list_content = "\n".join([f"- {item}" for item in items])
        self.sections.append(f"## {title}\n{list_content}")
        return self

    def add_json_example(self, title: str, example: Dict[str, Any]):
        """添加JSON示例"""
        json_str = json.dumps(example, ensure_ascii=False, indent=2)
        self.sections.append(f"## {title}\n```json\n{json_str}\n```")
        return self

    def build(self) -> str:
        """构建最终提示词"""
        return "\n\n".join(self.sections)
