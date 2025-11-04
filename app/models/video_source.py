"""
视频来源模型
支持本地文件、OSS URL和外部URL三种来源
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ValidationInfo


class VideoSourceType(str, Enum):
    """视频来源类型枚举"""
    LOCAL = "local"      # 本地文件路径
    OSS = "oss"          # 阿里云OSS URL
    URL = "url"          # 外部HTTP/HTTPS URL


class VideoSource(BaseModel):
    """
    视频来源定义

    支持三种来源类型：
    1. local: 本地文件路径（绝对路径）
    2. oss: 阿里云OSS对象URL
    3. url: 外部可访问的视频URL
    """

    type: VideoSourceType = Field(
        ...,
        description="视频来源类型"
    )

    # local类型参数
    path: Optional[str] = Field(
        None,
        description="本地文件绝对路径（type=local时必填）"
    )

    # oss/url类型参数
    url: Optional[str] = Field(
        None,
        description="OSS URL或外部URL（type=oss/url时必填）"
    )

    # 可选：自定义压缩配置（覆盖全局配置）
    compression_profile: Optional[str] = Field(
        None,
        description="压缩策略: aggressive/balanced/conservative/dynamic"
    )

    @field_validator('path')
    @classmethod
    def validate_path(cls, v, info: ValidationInfo):
        """验证local类型必须提供path"""
        if info.data.get('type') == VideoSourceType.LOCAL:
            if not v:
                raise ValueError("type=local时必须提供path参数")
        return v

    @field_validator('url')
    @classmethod
    def validate_url(cls, v, info: ValidationInfo):
        """验证oss/url类型必须提供url"""
        source_type = info.data.get('type')
        if source_type in [VideoSourceType.OSS, VideoSourceType.URL]:
            if not v:
                raise ValueError(f"type={source_type}时必须提供url参数")
            # 基本URL格式验证
            if not (v.startswith('http://') or v.startswith('https://')):
                raise ValueError("url必须以http://或https://开头")
        return v

    class Config:
        use_enum_values = True


class CompressionProfile(BaseModel):
    """压缩配置档案"""

    name: str = Field(..., description="配置名称")
    max_resolution: str = Field(..., description="最大分辨率: 480p/720p/1080p")
    target_fps: int = Field(..., description="目标帧率")
    video_bitrate: str = Field(..., description="视频码率")
    audio_bitrate: str = Field(..., description="音频码率")
    audio_sample_rate: int = Field(..., description="音频采样率")
    video_codec: str = Field(default="libx264", description="视频编码器")
    preset: str = Field(..., description="编码预设: ultrafast/fast/medium/slow")
    crf: int = Field(..., description="质量参数 (18-28, 越小质量越好)")

    @field_validator('crf')
    @classmethod
    def validate_crf(cls, v):
        """验证CRF范围"""
        if not 18 <= v <= 28:
            raise ValueError("CRF必须在18-28之间")
        return v

    @field_validator('max_resolution')
    @classmethod
    def validate_resolution(cls, v):
        """验证分辨率"""
        if v not in ['480p', '720p', '1080p']:
            raise ValueError("分辨率必须是480p/720p/1080p之一")
        return v


# 预设压缩策略
COMPRESSION_PROFILES = {
    "aggressive": CompressionProfile(
        name="aggressive",
        max_resolution="480p",
        target_fps=10,
        video_bitrate="500k",
        audio_bitrate="64k",
        audio_sample_rate=22050,
        preset="ultrafast",
        crf=28
    ),

    "balanced": CompressionProfile(
        name="balanced",
        max_resolution="720p",
        target_fps=15,
        video_bitrate="1500k",
        audio_bitrate="128k",
        audio_sample_rate=44100,
        preset="fast",
        crf=23
    ),

    "conservative": CompressionProfile(
        name="conservative",
        max_resolution="1080p",
        target_fps=24,
        video_bitrate="3000k",
        audio_bitrate="192k",
        audio_sample_rate=44100,
        preset="medium",
        crf=20
    ),
}

# 动态压缩规则：根据视频时长自动选择策略
DYNAMIC_COMPRESSION_RULES = {
    (0, 180): "conservative",      # 0-3分钟：保守压缩
    (180, 420): "balanced",        # 3-7分钟：平衡压缩
    (420, 600): "aggressive",      # 7-10分钟：激进压缩
}


def get_dynamic_compression_profile(duration: float) -> CompressionProfile:
    """
    根据视频时长动态选择压缩策略

    Args:
        duration: 视频时长（秒）

    Returns:
        CompressionProfile: 压缩配置档案
    """
    for (min_dur, max_dur), profile_name in DYNAMIC_COMPRESSION_RULES.items():
        if min_dur <= duration < max_dur:
            return COMPRESSION_PROFILES[profile_name]

    # 默认返回balanced
    return COMPRESSION_PROFILES["balanced"]
