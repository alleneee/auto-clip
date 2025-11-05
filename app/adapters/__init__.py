"""
AI服务适配器模块
实现依赖倒置原则（DIP）
"""

from app.adapters.vision_adapters import DashScopeVisionAdapter
from app.adapters.audio_adapters import ParaformerSpeechAdapter
from app.adapters.text_adapters import DashScopeTextAdapter
from app.adapters.tts_adapters import DashScopeTTSAdapter

__all__ = [
    "DashScopeVisionAdapter",
    "ParaformerSpeechAdapter",
    "DashScopeTextAdapter",
    "DashScopeTTSAdapter",
]
