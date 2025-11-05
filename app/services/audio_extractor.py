"""
音频提取服务 - 符合单一职责原则
职责: 从视频中提取音频用于语音识别（业务编排层）

重构说明：
- 底层音频操作已抽取到 app/utils/audio_utils.py
- 本服务类只负责业务编排和异常处理
"""
import os
from app.core.exceptions import AnalysisError
from app.utils.logger import get_logger
from app.utils.audio_utils import extract_audio_from_video

logger = get_logger(__name__)


class AudioExtractor:
    """
    音频提取器 (SRP: 单一职责)
    职责: 从视频提取符合ASR要求的音频（业务编排）
    底层操作: 调用 audio_utils.extract_audio_from_video
    """

    async def extract_audio(
        self,
        video_path: str,
        output_path: str
    ) -> str:
        """
        从视频中提取音频用于语音识别

        提取的音频格式符合Paraformer ASR要求：
        - 采样率：16kHz
        - 声道：单声道
        - 编码：PCM 16位

        Args:
            video_path: 视频文件路径
            output_path: 输出音频文件路径（建议使用.wav格式）

        Returns:
            音频文件路径

        Raises:
            AnalysisError: 音频提取失败时抛出
        """
        try:
            logger.info("extracting_audio_for_asr", video_path=video_path)

            # 调用底层工具函数进行音频提取
            # 使用Paraformer ASR要求的格式
            result_path = extract_audio_from_video(
                video_path=video_path,
                output_path=output_path,
                audio_codec='pcm_s16le',  # PCM 16位小端编码
                bitrate='192k',
                fps=16000,                 # 16kHz采样率（Paraformer要求）
                nbytes=2,                  # 16位 = 2字节
                ffmpeg_params=["-ac", "1"] # 单声道
            )

            # 业务层验证
            if not os.path.exists(result_path):
                raise AnalysisError(f"音频文件提取后未找到: {result_path}")

            file_size = os.path.getsize(result_path)
            logger.info(
                "audio_extracted_successfully",
                output_path=result_path,
                file_size_mb=file_size / (1024 * 1024)
            )

            return result_path

        except FileNotFoundError as e:
            logger.error("video_file_not_found", error=str(e))
            raise AnalysisError(f"视频文件不存在: {video_path}")
        except RuntimeError as e:
            # 捕获工具函数抛出的RuntimeError
            error_msg = str(e)
            if "没有音轨" in error_msg:
                logger.warning("video_has_no_audio", video_path=video_path)
                raise AnalysisError(f"视频文件不包含音频轨道: {video_path}")
            else:
                logger.error("audio_extraction_failed", error=error_msg)
                raise AnalysisError(f"音频提取失败: {error_msg}")
        except AnalysisError:
            raise
        except Exception as e:
            logger.error(
                "unexpected_audio_extraction_error",
                error=str(e),
                video_path=video_path
            )
            raise AnalysisError(f"音频提取过程发生未知错误: {str(e)}")
