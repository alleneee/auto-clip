"""
视频预处理服务 - 符合单一职责原则
职责: 视频压缩和base64编码转换（业务编排层）
底层操作: 使用 video_utils 工具函数

重构说明：
- compress_and_encode() 使用 video_utils.video_to_base64()
- Service层专注业务编排、状态管理、异常处理
"""
import tempfile
from typing import Tuple, List
import os

from app.core.exceptions import AnalysisError
from app.utils.logger import get_logger
from app.utils.video_utils import video_to_base64

logger = get_logger(__name__)


class VideoPreprocessor:
    """
    视频预处理器 (SRP: 单一职责)
    职责: 视频压缩和格式转换
    """

    def __init__(self, compression_service):
        """
        依赖注入 (DIP: 依赖倒置)

        Args:
            compression_service: 视频压缩服务 (IVideoCompressionService)
        """
        self.compression_service = compression_service

    async def compress_and_encode(
        self,
        video_path: str,
        profile_name: str = "balanced"
    ) -> Tuple[str, str, float, List[str]]:
        """
        压缩视频并转换为base64编码（业务编排）

        Args:
            video_path: 原始视频路径
            profile_name: 压缩配置名称

        Returns:
            Tuple[压缩后路径, base64编码, 压缩率, 临时文件列表]

        Raises:
            AnalysisError: 预处理失败
        """
        temp_files = []

        try:
            # 1. 压缩视频
            compressed_video_path = tempfile.mktemp(suffix=".mp4", prefix="compressed_")
            temp_files.append(compressed_video_path)

            logger.info(
                "compressing_video",
                input=video_path,
                output=compressed_video_path,
                profile=profile_name
            )

            compressed_path, stats = await self.compression_service.compress_video(
                input_path=video_path,
                output_path=compressed_video_path,
                profile_name=profile_name
            )

            compression_ratio = stats.get('compression_ratio', 0)

            logger.info(
                "video_compressed",
                compression_ratio=f"{compression_ratio * 100:.1f}%",
                original_size_mb=stats['original_size'] / (1024 * 1024),
                compressed_size_mb=stats['compressed_size'] / (1024 * 1024)
            )

            # 2. 转换为base64（使用工具函数）
            logger.info("converting_video_to_base64")
            
            # 调用底层工具函数
            video_base64 = video_to_base64(compressed_path)

            logger.info(
                "video_base64_ready",
                base64_length=len(video_base64)
            )

            return compressed_path, video_base64, compression_ratio, temp_files

        except Exception as e:
            logger.error("video_preprocessing_failed", error=str(e))
            # 清理临时文件
            self._cleanup_temp_files(temp_files)
            raise AnalysisError(f"视频预处理失败: {str(e)}")

    def _cleanup_temp_files(self, temp_files: List[str]) -> None:
        """清理临时文件"""
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception as cleanup_error:
                    logger.warning(
                        "temp_file_cleanup_failed",
                        file=temp_file,
                        error=str(cleanup_error)
                    )
