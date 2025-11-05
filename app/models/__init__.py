"""
数据模型模块
Pydantic 模型定义
"""
from .video import VideoMetadata, VideoImportRequest
from .task import Task
from .clip_decision import ClipDecision
from .responses import (
    ErrorDetail,
    SuccessResponse,
    ErrorResponse,
    ValidationErrorResponse
)
from .video_source import (
    VideoSourceType,
    VideoSource,
    CompressionProfile,
    COMPRESSION_PROFILES,
    get_dynamic_compression_profile
)
from .batch_processing import (
    BatchProcessStatus,
    VideoAnalysisResult,
    ClipSegment,
    ClipPlan,
    BatchProcessRequest,
    BatchProcessResponse,
    TaskStatusResponse
)

__all__ = [
    # 核心模型
    "VideoMetadata",
    "VideoImportRequest",
    "Task",
    "ClipDecision",
    "ErrorDetail",
    "SuccessResponse",
    "ErrorResponse",
    "ValidationErrorResponse",

    # 视频源模型
    "VideoSourceType",
    "VideoSource",
    "CompressionProfile",
    "COMPRESSION_PROFILES",
    "get_dynamic_compression_profile",

    # 批处理模型
    "BatchProcessStatus",
    "VideoAnalysisResult",
    "ClipSegment",
    "ClipPlan",
    "BatchProcessRequest",
    "BatchProcessResponse",
    "TaskStatusResponse",
]
