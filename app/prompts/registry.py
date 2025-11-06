"""
提示词注册表系统
提供提示词的动态注册、查找和管理功能
"""

from typing import Dict, List, Type, Optional, Any
import json

from app.prompts.base import BasePrompt
from app.prompts.metadata import ModelType, PromptCategory


class PromptRegistry:
    """提示词注册表（单例模式）"""

    _prompts: Dict[str, Type[BasePrompt]] = {}
    _instances: Dict[str, BasePrompt] = {}

    @classmethod
    def register(cls, category: str, name: str):
        """
        装饰器：注册提示词类

        使用方式:
            @PromptRegistry.register(category="clip_decision", name="enhanced")
            class EnhancedClipDecisionPrompt(BasePrompt):
                pass

        Args:
            category: 类别名
            name: 提示词名称
        """
        def decorator(prompt_class: Type[BasePrompt]):
            key = f"{category}.{name}"
            cls._prompts[key] = prompt_class
            return prompt_class
        return decorator

    @classmethod
    def get(cls, key: str) -> Optional[BasePrompt]:
        """
        获取提示词实例（单例）

        Args:
            key: 提示词键名，格式为 "category.name"

        Returns:
            提示词实例，如果不存在返回None
        """
        if key not in cls._prompts:
            return None

        # 如果已实例化，直接返回
        if key in cls._instances:
            return cls._instances[key]

        # 创建新实例
        prompt_class = cls._prompts[key]
        instance = prompt_class()
        cls._instances[key] = instance

        return instance

    @classmethod
    def search(
        cls,
        category: Optional[str] = None,
        model_type: Optional[ModelType] = None,
        tags: Optional[List[str]] = None,
        min_success_rate: Optional[float] = None
    ) -> List[Type[BasePrompt]]:
        """
        搜索提示词

        Args:
            category: 类别过滤
            model_type: 模型类型过滤
            tags: 标签过滤（匹配任意标签）
            min_success_rate: 最小成功率过滤

        Returns:
            匹配的提示词类列表
        """
        results = []

        for key, prompt_class in cls._prompts.items():
            # 实例化以访问元数据
            instance = cls.get(key)
            if not instance:
                continue

            # 类别过滤
            if category and instance.metadata.category != category:
                continue

            # 模型类型过滤
            if model_type and instance.metadata.model_type != model_type:
                continue

            # 标签过滤
            if tags:
                if not any(tag in instance.metadata.tags for tag in tags):
                    continue

            # 成功率过滤
            if min_success_rate is not None:
                if instance.metadata.success_rate < min_success_rate:
                    continue

            results.append(prompt_class)

        return results

    @classmethod
    def get_best_prompt(
        cls,
        category: str,
        model_type: ModelType
    ) -> Optional[Type[BasePrompt]]:
        """
        获取最佳提示词（基于成功率）

        Args:
            category: 类别
            model_type: 模型类型

        Returns:
            成功率最高的提示词类
        """
        candidates = cls.search(category=category, model_type=model_type)

        if not candidates:
            return None

        # 按成功率排序
        best = max(
            candidates,
            key=lambda c: cls.get(f"{category}.{c.__name__.lower().replace('prompt', '')}").metadata.success_rate
        )

        return best

    @classmethod
    def get_catalog(cls) -> Dict[str, Type[BasePrompt]]:
        """获取所有已注册的提示词"""
        return cls._prompts.copy()

    @classmethod
    def list_by_category(cls, category: str) -> List[str]:
        """
        列出某类别下的所有提示词

        Args:
            category: 类别名

        Returns:
            该类别下的提示词键名列表
        """
        return [
            key for key in cls._prompts.keys()
            if key.startswith(f"{category}.")
        ]

    @classmethod
    def export_catalog(cls, output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        导出提示词目录（JSON格式）

        Args:
            output_path: 输出文件路径，如果为None则只返回字典

        Returns:
            提示词目录字典
        """
        catalog = {}

        for key, prompt_class in cls._prompts.items():
            instance = cls.get(key)
            if instance:
                catalog[key] = instance.metadata.to_dict()

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(catalog, f, ensure_ascii=False, indent=2)

        return catalog

    @classmethod
    def clear(cls):
        """清空注册表（主要用于测试）"""
        cls._prompts.clear()
        cls._instances.clear()

    @classmethod
    def get_statistics(cls) -> Dict[str, Any]:
        """
        获取注册表统计信息

        Returns:
            统计信息字典
        """
        total_prompts = len(cls._prompts)
        categories = set()
        model_types = set()
        total_calls = 0
        avg_success_rate = 0.0

        for key in cls._prompts.keys():
            instance = cls.get(key)
            if instance:
                categories.add(instance.metadata.category)
                model_types.add(instance.metadata.model_type.value)
                total_calls += instance.metadata.total_calls
                avg_success_rate += instance.metadata.success_rate

        if total_prompts > 0:
            avg_success_rate /= total_prompts

        return {
            "total_prompts": total_prompts,
            "categories": list(categories),
            "model_types": list(model_types),
            "total_calls": total_calls,
            "avg_success_rate": f"{avg_success_rate:.2%}"
        }
