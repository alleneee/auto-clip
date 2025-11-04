"""
任务状态管理模型
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """任务状态枚举"""

    PENDING = "pending"  # 待处理
    ANALYZING = "analyzing"  # 分析中
    LLM_PASS1 = "llm_pass1"  # LLM第一轮处理
    LLM_PASS2 = "llm_pass2"  # LLM第二轮处理
    CLIPPING = "clipping"  # 剪辑中
    UPLOADING = "uploading"  # 上传中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消


class Task(BaseModel):
    """任务模型"""

    task_id: str = Field(..., description="任务ID")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="任务状态")
    progress: float = Field(default=0.0, ge=0.0, le=100.0, description="进度百分比")
    current_step: str = Field(default="初始化", description="当前步骤描述")
    video_ids: List[str] = Field(default_factory=list, description="关联的视频ID列表")
    result_url: Optional[str] = Field(None, description="最终结果URL")
    error_message: Optional[str] = Field(None, description="错误信息")
    error_traceback: Optional[str] = Field(None, description="错误堆栈")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="任务元数据")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = Field(None, description="完成时间")

    def update_status(
        self,
        status: TaskStatus,
        progress: Optional[float] = None,
        current_step: Optional[str] = None,
    ):
        """更新任务状态"""
        self.status = status
        self.updated_at = datetime.now()

        if progress is not None:
            self.progress = max(0.0, min(100.0, progress))

        if current_step is not None:
            self.current_step = current_step

        if status == TaskStatus.COMPLETED:
            self.progress = 100.0
            self.completed_at = datetime.now()
        elif status == TaskStatus.FAILED:
            self.completed_at = datetime.now()

    def set_error(self, error_message: str, error_traceback: Optional[str] = None):
        """设置错误信息"""
        self.status = TaskStatus.FAILED
        self.error_message = error_message
        self.error_traceback = error_traceback
        self.updated_at = datetime.now()
        self.completed_at = datetime.now()

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_xyz789",
                "status": "clipping",
                "progress": 65.0,
                "current_step": "正在剪辑第3个片段",
                "video_ids": ["vid_abc123", "vid_def456"],
                "result_url": None,
                "error_message": None,
                "metadata": {"user_id": "user_123", "priority": "normal"},
            }
        }


class TaskCreateRequest(BaseModel):
    """创建任务请求"""

    video_ids: List[str] = Field(..., min_items=1, description="要处理的视频ID列表")
    webhook_url: Optional[str] = Field(None, description="回调URL")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="任务配置")

    class Config:
        json_schema_extra = {
            "example": {
                "video_ids": ["vid_abc123", "vid_def456"],
                "webhook_url": "https://example.com/webhook",
                "config": {
                    "target_duration": 60,
                    "clip_count": 5,
                    "theme": "highlight"
                }
            }
        }


class TaskResponse(BaseModel):
    """任务响应"""

    task_id: str
    status: TaskStatus
    progress: float
    current_step: str
    result_url: Optional[str] = None
    created_at: datetime
    estimated_completion: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_xyz789",
                "status": "analyzing",
                "progress": 25.0,
                "current_step": "分析视频元数据",
                "result_url": None,
                "created_at": "2024-01-01T10:00:00",
            }
        }
