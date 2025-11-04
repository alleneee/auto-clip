"""
统一响应模型
定义标准的API响应格式
"""
from typing import Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """错误详情"""

    code: str = Field(..., description="错误代码")
    message: str = Field(..., description="错误消息")
    field: Optional[str] = Field(None, description="错误字段（验证错误）")
    detail: Optional[Any] = Field(None, description="详细信息（仅开发环境）")


class SuccessResponse(BaseModel):
    """成功响应"""

    success: bool = Field(default=True, description="请求是否成功")
    data: Any = Field(..., description="响应数据")
    message: Optional[str] = Field(None, description="消息")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间")
    request_id: Optional[str] = Field(None, description="请求ID")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {"video_id": "vid_abc123"},
                "message": "操作成功",
                "timestamp": "2024-01-01T10:00:00",
                "request_id": "req_xyz789"
            }
        }


class ErrorResponse(BaseModel):
    """错误响应"""

    success: bool = Field(default=False, description="请求是否成功")
    error: ErrorDetail = Field(..., description="错误详情")
    path: Optional[str] = Field(None, description="请求路径")
    method: Optional[str] = Field(None, description="HTTP方法")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间")
    request_id: Optional[str] = Field(None, description="请求ID")

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": {
                    "code": "VIDEO_NOT_FOUND",
                    "message": "视频不存在",
                    "field": None,
                    "detail": None
                },
                "path": "/api/v1/videos/vid_invalid",
                "method": "GET",
                "timestamp": "2024-01-01T10:00:00",
                "request_id": "req_xyz789"
            }
        }


class ValidationErrorResponse(BaseModel):
    """验证错误响应"""

    success: bool = Field(default=False, description="请求是否成功")
    error: str = Field(default="VALIDATION_ERROR", description="错误类型")
    message: str = Field(default="请求参数验证失败", description="错误消息")
    errors: list[ErrorDetail] = Field(..., description="验证错误列表")
    path: Optional[str] = Field(None, description="请求路径")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间")
    request_id: Optional[str] = Field(None, description="请求ID")

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "VALIDATION_ERROR",
                "message": "请求参数验证失败",
                "errors": [
                    {
                        "code": "VALUE_ERROR",
                        "message": "视频格式不支持",
                        "field": "file",
                        "detail": None
                    }
                ],
                "path": "/api/v1/videos/upload",
                "timestamp": "2024-01-01T10:00:00",
                "request_id": "req_xyz789"
            }
        }
