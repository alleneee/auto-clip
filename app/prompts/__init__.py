"""
提示词管理包
集中管理所有LLM调用的提示词
"""
# 旧版提示词（保留向后兼容）
from app.prompts.llm_prompts import (
    VideoAnalysisPrompts,
    ThemeGenerationPrompts,
    ClipDecisionPrompts,
    PromptTemplates,
    AudioTranscriptPrompts,
)

# 新版提示词系统
from app.prompts.registry import PromptRegistry
from app.prompts.metadata import (
    PromptMetadata,
    ModelType,
    OutputFormat,
    PromptCategory,
    PromptVersion
)
from app.prompts.base import (
    BasePrompt,
    VisionPrompt,
    TextPrompt,
    MultimodalPrompt,
    PromptBuilder
)

# 导入所有需要注册的提示词类（触发装饰器注册）
try:
    from app.prompts.clip_decision.enhanced import EnhancedClipDecisionPrompt
except ImportError:
    EnhancedClipDecisionPrompt = None


def initialize_prompts():
    """
    初始化提示词系统

    Returns:
        已注册的提示词目录
    """
    catalog = PromptRegistry.get_catalog()
    print(f"✅ 提示词系统已初始化")
    print(f"📊 已注册 {len(catalog)} 个提示词模板:")
    for key in catalog:
        print(f"  - {key}")
    return catalog


def get_prompt(key: str):
    """
    获取提示词实例的快捷方法

    Args:
        key: 提示词键名，格式为 "category.name"

    Returns:
        提示词实例
    """
    return PromptRegistry.get(key)


__all__ = [
    # 旧版（向后兼容）
    "VideoAnalysisPrompts",
    "ThemeGenerationPrompts",
    "ClipDecisionPrompts",
    "PromptTemplates",
    "AudioTranscriptPrompts",

    # 新版系统
    'PromptRegistry',
    'initialize_prompts',
    'get_prompt',
    'PromptMetadata',
    'ModelType',
    'OutputFormat',
    'PromptCategory',
    'PromptVersion',
    'BasePrompt',
    'VisionPrompt',
    'TextPrompt',
    'MultimodalPrompt',
    'PromptBuilder',
]

if EnhancedClipDecisionPrompt:
    __all__.append('EnhancedClipDecisionPrompt')
