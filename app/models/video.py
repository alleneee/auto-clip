"""
视频数据模型
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class VideoMetadata(BaseModel):
    """视频元数据模型"""

    video_id: str = Field(..., description="视频唯一标识")
    filename: str = Field(..., description="原始文件名")
    duration: float = Field(..., description="视频时长（秒）")
    width: int = Field(..., description="视频宽度")
    height: int = Field(..., description="视频高度")
    fps: float = Field(..., description="帧率")
    codec: str = Field(..., description="视频编码格式")
    audio_present: bool = Field(default=True, description="是否包含音频")
    audio_codec: Optional[str] = Field(None, description="音频编码格式")
    file_size: int = Field(..., description="文件大小（字节）")
    bitrate: Optional[int] = Field(None, description="比特率")
    storage_path: str = Field(..., description="本地存储路径")
    oss_url: Optional[str] = Field(None, description="OSS存储URL")
    created_at: datetime = Field(default_factory=datetime.now)

    @property
    def resolution(self) -> str:
        """分辨率字符串"""
        return f"{self.width}x{self.height}"

    @property
    def duration_str(self) -> str:
        """格式化时长"""
        minutes = int(self.duration // 60)
        seconds = int(self.duration % 60)
        return f"{minutes:02d}:{seconds:02d}"

    class Config:
        json_schema_extra = {
            "example": {
                "video_id": "vid_abc123",
                "filename": "sample.mp4",
                "duration": 120.5,
                "width": 1920,
                "height": 1080,
                "fps": 30.0,
                "codec": "h264",
                "audio_present": True,
                "audio_codec": "aac",
                "file_size": 104857600,
                "bitrate": 5000000,
                "storage_path": "/storage/uploads/vid_abc123.mp4",
            }
        }


class VideoImportRequest(BaseModel):
    """视频导入请求"""

    import_type: str = Field(..., description="导入类型: upload, url, oss")
    url: Optional[str] = Field(None, description="URL地址（url类型）")
    oss_path: Optional[str] = Field(None, description="OSS路径（oss类型）")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="额外元数据")

    class Config:
        json_schema_extra = {
            "example": {
                "import_type": "url",
                "url": "https://example.com/video.mp4",
                "metadata": {"source": "youtube", "user_id": "12345"}
            }
        }
