"""
服务工厂 - 依赖注入容器 (DIP: 依赖倒置原则)

职责:
- 创建和组装所有服务
- 管理服务依赖关系
- 提供服务实例获取接口
"""
from typing import Optional

from app.services.video_preprocessor import VideoPreprocessor
from app.services.audio_extractor import AudioExtractor
from app.adapters import (
    DashScopeVisionAdapter,
    ParaformerSpeechAdapter,
    DashScopeTextAdapter
)
from app.services.video_analysis_orchestrator import VideoAnalysisOrchestrator
from app.services.video_compression import video_compression_service
from app.utils.oss_client import oss_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ServiceFactory:
    """
    服务工厂 (依赖注入容器)

    实现SOLID原则:
    - SRP: 单一职责 - 仅负责服务创建和组装
    - OCP: 开闭原则 - 新增服务提供商只需添加新适配器
    - DIP: 依赖倒置 - 所有服务通过工厂创建，依赖抽象接口
    """

    _instance = None  # 单例实例

    def __new__(cls):
        """单例模式 - 确保全局只有一个工厂实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化工厂"""
        if self._initialized:
            return

        logger.info("initializing_service_factory")

        # 基础服务（无依赖）
        self._vision_service = None
        self._speech_service = None
        self._text_service = None
        self._video_preprocessor = None
        self._audio_extractor = None
        self._storage_service = None

        # 编排器（依赖其他服务）
        self._orchestrator = None

        self._initialized = True
        logger.info("service_factory_initialized")

    def get_vision_service(self, api_key: Optional[str] = None):
        """
        获取视觉分析服务

        OCP: 开闭原则 - 可以轻松替换为其他服务提供商
        例如: GoogleVisionAdapter, AWSRekognitionAdapter

        Args:
            api_key: API密钥（可选）

        Returns:
            IVisionAnalysisService实现
        """
        if self._vision_service is None:
            logger.info("creating_vision_service", provider="dashscope")
            self._vision_service = DashScopeVisionAdapter(api_key=api_key)

        return self._vision_service

    def get_speech_service(self, api_key: Optional[str] = None):
        """
        获取语音识别服务

        OCP: 开闭原则 - 可以轻松替换为其他ASR服务
        例如: GoogleSpeechAdapter, AzureSpeechAdapter

        Args:
            api_key: API密钥（可选）

        Returns:
            ISpeechRecognitionService实现
        """
        if self._speech_service is None:
            logger.info("creating_speech_service", provider="paraformer")
            self._speech_service = ParaformerSpeechAdapter(api_key=api_key)

        return self._speech_service

    def get_text_service(self, api_key: Optional[str] = None):
        """
        获取文本生成服务

        Args:
            api_key: API密钥（可选）

        Returns:
            ITextGenerationService实现
        """
        if self._text_service is None:
            logger.info("creating_text_service", provider="dashscope")
            self._text_service = DashScopeTextAdapter(api_key=api_key)

        return self._text_service

    def get_video_preprocessor(self):
        """
        获取视频预处理器

        Returns:
            VideoPreprocessor实例
        """
        if self._video_preprocessor is None:
            logger.info("creating_video_preprocessor")
            # 注入压缩服务依赖
            self._video_preprocessor = VideoPreprocessor(
                compression_service=video_compression_service
            )

        return self._video_preprocessor

    def get_audio_extractor(self):
        """
        获取音频提取器

        Returns:
            AudioExtractor实例
        """
        if self._audio_extractor is None:
            logger.info("creating_audio_extractor")
            self._audio_extractor = AudioExtractor()

        return self._audio_extractor

    def get_storage_service(self):
        """
        获取存储服务

        OCP: 开闭原则 - 可以轻松替换为其他存储服务
        例如: S3StorageAdapter, LocalStorageAdapter

        Returns:
            IStorageService实现
        """
        if self._storage_service is None:
            logger.info("creating_storage_service", provider="oss")
            self._storage_service = oss_client

        return self._storage_service

    def get_video_analysis_orchestrator(self) -> VideoAnalysisOrchestrator:
        """
        获取视频分析编排器（核心服务）

        DIP: 依赖倒置 - 通过依赖注入组装所有服务

        Returns:
            VideoAnalysisOrchestrator实例
        """
        if self._orchestrator is None:
            logger.info("creating_video_analysis_orchestrator")

            # 依赖注入 - 传入所有依赖服务
            self._orchestrator = VideoAnalysisOrchestrator(
                vision_service=self.get_vision_service(),
                speech_service=self.get_speech_service(),
                text_service=self.get_text_service(),
                video_preprocessor=self.get_video_preprocessor(),
                audio_extractor=self.get_audio_extractor(),
                storage_service=self.get_storage_service()
            )

        return self._orchestrator

    def reset(self):
        """
        重置工厂（主要用于测试）

        清除所有缓存的服务实例，下次调用get_*方法时会重新创建
        """
        logger.info("resetting_service_factory")
        self._vision_service = None
        self._speech_service = None
        self._text_service = None
        self._video_preprocessor = None
        self._audio_extractor = None
        self._storage_service = None
        self._orchestrator = None
        logger.info("service_factory_reset_complete")


# 全局工厂实例
service_factory = ServiceFactory()


# ============================================
# 便捷函数 - 快速获取常用服务
# ============================================

def get_video_analyzer() -> VideoAnalysisOrchestrator:
    """
    快速获取视频分析器（推荐使用）

    Returns:
        VideoAnalysisOrchestrator实例（已注入所有依赖）
    """
    return service_factory.get_video_analysis_orchestrator()
