"""
视频分析服务
使用FFmpeg提取视频元数据
"""
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from typing import List
import ffmpeg

from app.models.video import VideoMetadata
from app.core.exceptions import AnalysisError, VideoNotFoundError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class VideoAnalyzer:
    """视频分析器"""

    def __init__(self, max_workers: int = 4):
        """
        初始化分析器

        Args:
            max_workers: 最大并行线程数
        """
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    async def analyze_video(self, video_path: str, video_id: str) -> VideoMetadata:
        """
        分析单个视频

        Args:
            video_path: 视频文件路径
            video_id: 视频ID

        Returns:
            视频元数据
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, self._extract_metadata, video_path, video_id
        )

    async def analyze_videos_parallel(
        self, video_paths: List[tuple[str, str]]
    ) -> List[VideoMetadata]:
        """
        并行分析多个视频

        Args:
            video_paths: (视频路径, 视频ID) 元组列表

        Returns:
            视频元数据列表
        """
        logger.info("starting_parallel_analysis", video_count=len(video_paths))

        tasks = [
            self.analyze_video(path, vid_id) for path, vid_id in video_paths
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 过滤错误
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "video_analysis_failed",
                    video_id=video_paths[i][1],
                    error=str(result),
                )
            else:
                valid_results.append(result)

        logger.info(
            "parallel_analysis_completed",
            total=len(video_paths),
            success=len(valid_results),
            failed=len(video_paths) - len(valid_results),
        )

        return valid_results

    def _extract_metadata(self, video_path: str, video_id: str) -> VideoMetadata:
        """
        使用FFmpeg提取视频元数据

        Args:
            video_path: 视频文件路径
            video_id: 视频ID

        Returns:
            视频元数据

        Raises:
            VideoNotFoundError: 视频不存在
            AnalysisError: 分析失败
        """
        if not os.path.exists(video_path):
            raise VideoNotFoundError(f"视频文件不存在: {video_path}")

        try:
            # 使用FFprobe获取信息
            probe = ffmpeg.probe(video_path)

            # 提取视频流信息
            video_stream = next(
                (s for s in probe["streams"] if s["codec_type"] == "video"), None
            )

            if not video_stream:
                raise AnalysisError("未找到视频流")

            # 提取音频流信息
            audio_stream = next(
                (s for s in probe["streams"] if s["codec_type"] == "audio"), None
            )

            # 构建元数据
            metadata = VideoMetadata(
                video_id=video_id,
                filename=os.path.basename(video_path),
                duration=float(probe["format"].get("duration", 0)),
                width=int(video_stream.get("width", 0)),
                height=int(video_stream.get("height", 0)),
                fps=self._parse_fps(video_stream.get("r_frame_rate", "30/1")),
                codec=video_stream.get("codec_name", "unknown"),
                audio_present=audio_stream is not None,
                audio_codec=audio_stream.get("codec_name") if audio_stream else None,
                file_size=int(probe["format"].get("size", 0)),
                bitrate=int(probe["format"].get("bit_rate", 0)),
                storage_path=video_path,
            )

            logger.info(
                "video_analyzed",
                video_id=video_id,
                duration=metadata.duration,
                resolution=metadata.resolution,
                fps=metadata.fps,
            )

            return metadata

        except ffmpeg.Error as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            logger.error("ffmpeg_probe_failed", video_id=video_id, error=error_msg)
            raise AnalysisError(f"FFmpeg分析失败: {error_msg}")

        except Exception as e:
            logger.error("metadata_extraction_failed", video_id=video_id, error=str(e))
            raise AnalysisError(f"元数据提取失败: {str(e)}")

    def _parse_fps(self, fps_str: str) -> float:
        """
        解析帧率字符串

        Args:
            fps_str: 帧率字符串 (例如 "30/1", "29.97")

        Returns:
            帧率数值
        """
        try:
            if "/" in fps_str:
                num, den = fps_str.split("/")
                return float(num) / float(den)
            return float(fps_str)
        except:
            return 30.0  # 默认30fps
