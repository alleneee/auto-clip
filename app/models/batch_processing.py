"""
批处理请求和响应模型
支持多视频批量处理、AI分析和自动剪辑
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from enum import Enum

from .video_source import VideoSource


class BatchProcessStatus(str, Enum):
    """批处理状态枚举"""
    PENDING = "pending"              # 待处理
    PREPARING = "preparing"          # 准备中（下载、压缩）
    ANALYZING = "analyzing"          # AI分析中
    PLANNING = "planning"            # 生成剪辑方案
    CLIPPING = "clipping"           # 剪辑处理中
    COMPLETED = "completed"         # 已完成
    FAILED = "failed"               # 失败
    PARTIAL_SUCCESS = "partial_success"  # 部分成功


class VideoAnalysisResult(BaseModel):
    """单个视频的AI分析结果"""

    video_index: int = Field(..., description="视频索引（在批处理中的位置）")
    video_source: VideoSource = Field(..., description="原始视频来源")

    # 视频元信息
    duration: float = Field(..., description="视频时长（秒）")
    resolution: str = Field(..., description="分辨率，如 1920x1080")
    fps: float = Field(..., description="帧率")
    file_size: int = Field(..., description="文件大小（字节）")

    # 压缩信息
    compressed_oss_url: str = Field(..., description="压缩后的临时OSS地址")
    compression_profile: str = Field(..., description="使用的压缩策略")
    compression_ratio: float = Field(..., description="压缩比率（0-1）")

    # AI分析结果
    vl_analysis: Dict[str, Any] = Field(..., description="VL模型分析结果（原始JSON）")
    analysis_summary: str = Field(..., description="分析摘要文本")
    key_moments: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="关键时刻列表 [{'timestamp': float, 'description': str}]"
    )

    # 状态信息
    status: str = Field(default="completed", description="分析状态")
    error: Optional[str] = Field(None, description="错误信息（如果失败）")
    processing_time: float = Field(..., description="处理耗时（秒）")


class ClipSegment(BaseModel):
    """单个剪辑片段"""

    video_index: int = Field(..., description="来源视频索引")
    start_time: float = Field(..., ge=0, description="起始时间（秒）")
    end_time: float = Field(..., gt=0, description="结束时间（秒）")
    duration: float = Field(..., gt=0, description="片段时长（秒）")
    reason: str = Field(..., description="选择该片段的理由")
    priority: int = Field(default=0, description="优先级（用于排序）")

    @field_validator('end_time')
    @classmethod
    def validate_time_range(cls, v, info):
        """验证时间范围有效性"""
        start_time = info.data.get('start_time', 0)
        if v <= start_time:
            raise ValueError("结束时间必须大于起始时间")
        return v


class ClipPlan(BaseModel):
    """完整剪辑方案"""

    # 剪辑策略
    strategy: str = Field(..., description="剪辑策略描述")
    total_duration: float = Field(..., gt=0, description="预计总时长（秒）")
    segments: List[ClipSegment] = Field(..., min_length=1, description="剪辑片段列表")

    # 附加信息
    reasoning: str = Field(..., description="剪辑方案推理过程")
    quality_score: Optional[float] = Field(None, ge=0, le=1, description="质量评分（0-1）")

    @field_validator('total_duration')
    @classmethod
    def validate_total_duration(cls, v, info):
        """验证总时长与片段时长一致性"""
        segments = info.data.get('segments', [])
        if segments:
            calculated_duration = sum(seg.duration for seg in segments)
            # 允许5%的误差
            if abs(calculated_duration - v) > v * 0.05:
                raise ValueError(f"总时长不一致：声明 {v}秒，实际 {calculated_duration}秒")
        return v


class BatchProcessRequest(BaseModel):
    """批处理请求模型"""

    # 视频来源列表
    videos: List[VideoSource] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="视频来源列表（最多10个）"
    )

    # 全局配置
    global_compression_profile: str = Field(
        default="balanced",
        description="全局压缩策略: aggressive/balanced/conservative/dynamic"
    )

    # 临时存储配置
    temp_storage_expiry_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="临时文件过期时间（小时，1-168）"
    )

    # AI分析配置
    vl_model: str = Field(
        default="qwen-vl-plus",
        description="VL模型名称"
    )
    text_model: str = Field(
        default="qwen-plus",
        description="文本模型名称"
    )

    # 剪辑配置
    target_duration: Optional[float] = Field(
        None,
        gt=0,
        description="目标剪辑时长（秒），None表示自动决定"
    )
    clip_strategy: str = Field(
        default="highlights",
        description="剪辑策略: highlights/summary/custom"
    )

    # 输出配置
    output_quality: str = Field(
        default="high",
        description="输出质量: low/medium/high/source"
    )

    # 可选元信息
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="自定义元信息"
    )


class BatchProcessResponse(BaseModel):
    """批处理响应模型"""

    # 任务信息
    task_id: str = Field(..., description="任务ID")
    status: BatchProcessStatus = Field(..., description="批处理状态")

    # 进度信息
    total_videos: int = Field(..., description="总视频数")
    processed_videos: int = Field(default=0, description="已处理视频数")
    progress_percentage: float = Field(default=0, ge=0, le=100, description="进度百分比")

    # 分析结果
    vl_results: List[VideoAnalysisResult] = Field(
        default_factory=list,
        description="各视频的VL分析结果"
    )

    # 剪辑方案
    clip_plan: Optional[ClipPlan] = Field(None, description="生成的剪辑方案")

    # 最终输出
    final_video_url: Optional[str] = Field(None, description="最终剪辑视频的OSS公网地址")
    final_video_duration: Optional[float] = Field(None, description="最终视频时长（秒）")
    final_video_size: Optional[int] = Field(None, description="最终视频大小（字节）")

    # 成本与性能
    total_processing_time: Optional[float] = Field(None, description="总处理时间（秒）")
    estimated_token_usage: Optional[int] = Field(None, description="预估token使用量")
    token_cost_savings: Optional[float] = Field(None, description="token成本节省率（0-1）")

    # 时间戳
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")

    # 错误信息
    error: Optional[str] = Field(None, description="错误信息（如果失败）")
    failed_videos: List[int] = Field(default_factory=list, description="失败视频的索引列表")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaskStatusResponse(BaseModel):
    """任务状态查询响应"""

    task_id: str = Field(..., description="任务ID")
    status: BatchProcessStatus = Field(..., description="当前状态")
    progress_percentage: float = Field(..., ge=0, le=100, description="进度百分比")
    current_stage: str = Field(..., description="当前阶段描述")

    # 可选详细信息
    processed_videos: Optional[int] = Field(None, description="已处理视频数")
    total_videos: Optional[int] = Field(None, description="总视频数")
    estimated_remaining_time: Optional[float] = Field(None, description="预计剩余时间（秒）")

    error: Optional[str] = Field(None, description="错误信息")
