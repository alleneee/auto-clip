"""
提示词元数据管理系统
提供版本控制、性能跟踪、参数验证等功能
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime


class ModelType(str, Enum):
    """LLM模型类型"""
    VISION = "vision"  # 视觉模型（支持图片输入）
    TEXT = "text"  # 纯文本模型
    MULTIMODAL = "multimodal"  # 多模态模型
    AUDIO = "audio"  # 音频模型


class OutputFormat(str, Enum):
    """输出格式类型"""
    JSON = "json"
    TEXT = "text"
    MARKDOWN = "markdown"
    CODE = "code"


class PromptCategory(str, Enum):
    """提示词类别"""
    CLIP_DECISION = "clip_decision"
    NARRATION = "narration"
    ANALYSIS = "analysis"
    CUSTOM = "custom"


@dataclass
class PromptMetadata:
    """
    提示词元数据

    包含版本信息、性能指标、参数定义等完整的提示词元数据
    """
    # 基础信息
    name: str  # 提示词名称
    category: str  # 类别
    version: str  # 当前版本
    model_type: ModelType  # 模型类型
    output_format: OutputFormat  # 输出格式

    # 参数定义
    parameters: List[str] = field(default_factory=list)  # 必需参数列表
    optional_parameters: List[str] = field(default_factory=list)  # 可选参数

    # 描述信息
    description: str = ""  # 功能描述
    tags: List[str] = field(default_factory=list)  # 标签

    # 性能指标
    success_rate: float = 0.0  # 成功率 (0.0-1.0)
    avg_tokens: int = 0  # 平均Token消耗
    avg_latency: float = 0.0  # 平均延迟（秒）
    total_calls: int = 0  # 总调用次数
    failed_calls: int = 0  # 失败次数

    # 版本控制
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    changelog: List[str] = field(default_factory=list)  # 版本变更记录

    # 依赖信息
    dependencies: List[str] = field(default_factory=list)  # 依赖的其他提示词

    def validate_parameters(self, provided_params: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        验证提供的参数是否完整

        Args:
            provided_params: 提供的参数字典

        Returns:
            (是否有效, 缺失的参数列表)
        """
        missing = [p for p in self.parameters if p not in provided_params]
        return len(missing) == 0, missing

    def update_metrics(self, success: bool, tokens: int, latency: float):
        """
        更新性能指标（增量更新）

        使用移动平均算法，避免重新计算所有历史数据

        Args:
            success: 本次调用是否成功
            tokens: 本次Token消耗
            latency: 本次延迟（秒）
        """
        self.total_calls += 1

        if not success:
            self.failed_calls += 1

        # 更新成功率（移动平均）
        self.success_rate = (
            (self.success_rate * (self.total_calls - 1) + (1.0 if success else 0.0))
            / self.total_calls
        )

        # 更新平均Token
        self.avg_tokens = int(
            (self.avg_tokens * (self.total_calls - 1) + tokens)
            / self.total_calls
        )

        # 更新平均延迟
        self.avg_latency = (
            (self.avg_latency * (self.total_calls - 1) + latency)
            / self.total_calls
        )

        self.updated_at = datetime.now()

    def add_changelog_entry(self, entry: str):
        """添加版本变更记录"""
        timestamp = datetime.now().strftime("%Y-%m-%d")
        self.changelog.append(f"[{timestamp}] {entry}")
        self.updated_at = datetime.now()

    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        return {
            "name": self.name,
            "success_rate": f"{self.success_rate:.2%}",
            "avg_tokens": self.avg_tokens,
            "avg_latency": f"{self.avg_latency:.2f}s",
            "total_calls": self.total_calls,
            "failed_calls": self.failed_calls,
            "error_rate": f"{(self.failed_calls / max(self.total_calls, 1)):.2%}"
        }

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "category": self.category,
            "version": self.version,
            "model_type": self.model_type.value,
            "output_format": self.output_format.value,
            "parameters": self.parameters,
            "optional_parameters": self.optional_parameters,
            "description": self.description,
            "tags": self.tags,
            "performance": self.get_performance_summary(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "changelog": self.changelog,
            "dependencies": self.dependencies
        }


@dataclass
class PromptVersion:
    """提示词版本信息"""
    version: str
    template: str
    changelog: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    deprecated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "version": self.version,
            "template_preview": self.template[:200] + "..." if len(self.template) > 200 else self.template,
            "changelog": self.changelog,
            "created_at": self.created_at.isoformat(),
            "deprecated": self.deprecated
        }
