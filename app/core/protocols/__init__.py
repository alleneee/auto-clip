"""
领域抽象接口汇总导出 (SOLID: 依赖倒置原则)
所有服务依赖这些抽象，而不是具体实现
"""

# ============================================
# 导入所有协议接口
# ============================================

from app.core.protocols.vision_protocols import IVisionAnalysisService
from app.core.protocols.audio_protocols import ISpeechRecognitionService
from app.core.protocols.text_protocols import ITextGenerationService
from app.core.protocols.tts_protocols import ITTSService
from app.core.protocols.video_protocols import (
    IVideoPreprocessor,
    IVideoCompressionService,
    IAudioExtractor
)
from app.core.protocols.storage_protocols import IStorageService


# ============================================
# 统一导出
# ============================================

__all__ = [
    # 视觉分析
    "IVisionAnalysisService",

    # 音频语音识别
    "ISpeechRecognitionService",

    # 文本生成
    "ITextGenerationService",

    # 文本转语音
    "ITTSService",

    # 视频处理
    "IVideoPreprocessor",
    "IVideoCompressionService",
    "IAudioExtractor",

    # 存储服务
    "IStorageService",
]
