"""
配置管理模块
使用pydantic-settings进行环境变量管理和验证
"""
from functools import lru_cache
from typing import Optional, List
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置类"""

    # ===== 应用基础配置 =====
    APP_NAME: str = "Auto-Clip"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # ===== Redis配置 =====
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # ===== 存储配置 =====
    STORAGE_BACKEND: str = Field(default="hybrid", description="存储模式: local, oss, hybrid")
    LOCAL_STORAGE_PATH: str = "./storage"

    # 阿里云OSS配置
    OSS_ENDPOINT: Optional[str] = None
    OSS_ACCESS_KEY_ID: Optional[str] = None
    OSS_ACCESS_KEY_SECRET: Optional[str] = None
    OSS_BUCKET_NAME: Optional[str] = None
    OSS_REGION: str = "cn-hangzhou"

    # ===== AI服务配置 =====
    # DashScope
    DASHSCOPE_API_KEY: str = Field(..., description="DashScope API密钥")
    DASHSCOPE_VL_MODEL: str = "qwen-vl-plus"
    DASHSCOPE_TEXT_MODEL: str = "qwen-plus"

    # Paraformer
    PARAFORMER_APP_KEY: Optional[str] = None
    PARAFORMER_ACCESS_KEY_ID: Optional[str] = None
    PARAFORMER_ACCESS_KEY_SECRET: Optional[str] = None

    # ===== 任务配置 =====
    MAX_PARALLEL_ANALYSIS: int = Field(default=4, description="并行分析线程数")
    TASK_TIMEOUT: int = Field(default=3600, description="任务超时时间（秒）")
    WEBHOOK_TIMEOUT: int = Field(default=10, description="Webhook超时时间（秒）")

    # ===== 视频处理配置 =====
    MAX_VIDEO_SIZE: int = Field(
        default=2 * 1024 * 1024 * 1024,  # 2GB
        description="最大视频文件大小（字节）"
    )
    SUPPORTED_FORMATS: List[str] = Field(
        default=["mp4", "avi", "mov", "mkv", "flv", "wmv"],
        description="支持的视频格式"
    )
    OUTPUT_VIDEO_CODEC: str = "libx264"
    OUTPUT_AUDIO_CODEC: str = "aac"

    # ===== Webhook配置 =====
    WEBHOOK_URL: Optional[str] = None
    WEBHOOK_SECRET: Optional[str] = None

    @validator("SUPPORTED_FORMATS", pre=True)
    def parse_supported_formats(cls, v):
        """解析支持的格式列表"""
        if isinstance(v, str):
            return [fmt.strip() for fmt in v.split(",")]
        return v

    @validator("STORAGE_BACKEND")
    def validate_storage_backend(cls, v):
        """验证存储模式"""
        if v not in ["local", "oss", "hybrid"]:
            raise ValueError("STORAGE_BACKEND must be one of: local, oss, hybrid")
        return v

    @property
    def uploads_dir(self) -> str:
        """上传目录"""
        return f"{self.LOCAL_STORAGE_PATH}/uploads"

    @property
    def processed_dir(self) -> str:
        """处理后目录"""
        return f"{self.LOCAL_STORAGE_PATH}/processed"

    @property
    def cache_dir(self) -> str:
        """缓存目录"""
        return f"{self.LOCAL_STORAGE_PATH}/cache"

    @property
    def metadata_dir(self) -> str:
        """元数据目录"""
        return f"{self.LOCAL_STORAGE_PATH}/metadata"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    获取配置单例
    使用lru_cache确保配置只加载一次
    """
    return Settings()


# 便捷访问
settings = get_settings()
