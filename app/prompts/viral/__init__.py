"""
病毒式传播提示词模块
包含钩子和传播技巧
"""

from app.prompts.viral.hooks import (
    ViralHooks,
    HookType,
    VideoStyle,
    HookTemplate
)
from app.prompts.viral.techniques import ViralTechniques


__all__ = [
    'ViralHooks',
    'HookType',
    'VideoStyle',
    'HookTemplate',
    'ViralTechniques'
]
