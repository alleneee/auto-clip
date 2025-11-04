"""
视频内容综合分析服务
集成视觉分析(DashScope)和语音识别(Paraformer)
"""
from typing import Dict, Any, Optional, List
import asyncio

from app.models.video import VideoMetadata
from app.utils.ai_clients.dashscope_client import DashScopeClient
from app.utils.ai_clients.paraformer_client import ParaformerClient
from app.prompts import AudioTranscriptPrompts
from app.core.exceptions import AnalysisError, LLMServiceError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class VideoContentAnalyzer:
    """视频内容综合分析器"""

    def __init__(self):
        """初始化分析器"""
        self.dashscope_client = DashScopeClient()
        self.paraformer_client = ParaformerClient()

    async def analyze_full_content(
        self,
        video_path: str,
        audio_url: Optional[str] = None,
        enable_speech_recognition: bool = True,
        visual_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        完整的视频内容分析（视觉+语音）

        Args:
            video_path: 视频文件本地路径（用于视觉分析）
            audio_url: 音频文件的公网URL（用于语音识别）
                      如果为None且enable_speech_recognition=True，将跳过语音识别
            enable_speech_recognition: 是否启用语音识别
            visual_prompt: 自定义视觉分析提示词

        Returns:
            包含视觉分析、语音识别和综合分析的字典
        """
        try:
            logger.info(
                "starting_full_content_analysis",
                video_path=video_path,
                audio_url=audio_url,
                enable_speech=enable_speech_recognition,
            )

            # 并行执行视觉分析和语音识别
            tasks = []

            # 任务1：视觉内容分析
            visual_task = self.dashscope_client.analyze_video_visual(
                video_path, prompt=visual_prompt
            )
            tasks.append(("visual", visual_task))

            # 任务2：语音识别（如果启用）
            if enable_speech_recognition and audio_url:
                speech_task = self.paraformer_client.transcribe_audio(
                    file_url=audio_url, language_hints=["zh", "en"]
                )
                tasks.append(("speech", speech_task))

            # 并行执行
            results = await asyncio.gather(
                *[task for _, task in tasks], return_exceptions=True
            )

            # 处理结果
            analysis_result = {
                "visual_analysis": None,
                "transcript": None,
                "transcript_text": "",
                "has_speech": False,
                "fusion_analysis": None,
                "status": "success",
                "errors": [],
            }

            for i, (task_type, result) in enumerate(zip([t[0] for t in tasks], results)):
                if isinstance(result, Exception):
                    error_msg = str(result)
                    logger.error(f"{task_type}_analysis_failed", error=error_msg)
                    analysis_result["errors"].append(
                        {
                            "type": task_type,
                            "error": error_msg,
                        }
                    )
                    if task_type == "visual":
                        # 视觉分析失败是致命的
                        analysis_result["status"] = "failed"
                else:
                    if task_type == "visual":
                        analysis_result["visual_analysis"] = result
                    elif task_type == "speech":
                        analysis_result["transcript"] = result
                        analysis_result["transcript_text"] = (
                            self.paraformer_client.extract_full_text(result)
                        )
                        analysis_result["has_speech"] = True

            # 如果视觉分析失败，直接返回
            if analysis_result["status"] == "failed":
                logger.error("visual_analysis_failed_critical")
                return analysis_result

            # 如果有语音内容，进行音视频融合分析
            if analysis_result["has_speech"] and analysis_result["transcript_text"]:
                try:
                    fusion_analysis = await self._fuse_audio_visual_analysis(
                        visual_analysis=analysis_result["visual_analysis"],
                        transcript_text=analysis_result["transcript_text"],
                    )
                    analysis_result["fusion_analysis"] = fusion_analysis
                except Exception as e:
                    logger.warning("fusion_analysis_failed", error=str(e))
                    analysis_result["errors"].append(
                        {"type": "fusion", "error": str(e)}
                    )

            logger.info(
                "full_content_analysis_completed",
                has_visual=analysis_result["visual_analysis"] is not None,
                has_speech=analysis_result["has_speech"],
                has_fusion=analysis_result["fusion_analysis"] is not None,
            )

            return analysis_result

        except Exception as e:
            logger.error("full_content_analysis_exception", error=str(e))
            raise AnalysisError(f"视频内容分析失败: {str(e)}")

    async def analyze_batch_videos(
        self,
        video_configs: List[Dict[str, Any]],
        enable_speech_recognition: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        批量分析多个视频

        Args:
            video_configs: 视频配置列表，每项包含：
                {
                    "video_id": str,
                    "video_path": str,
                    "audio_url": Optional[str]
                }
            enable_speech_recognition: 是否启用语音识别

        Returns:
            分析结果列表
        """
        logger.info("starting_batch_analysis", video_count=len(video_configs))

        # 并行分析所有视频
        tasks = [
            self._analyze_single_video_with_id(
                video_id=config["video_id"],
                video_path=config["video_path"],
                audio_url=config.get("audio_url"),
                enable_speech_recognition=enable_speech_recognition,
            )
            for config in video_configs
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        analysis_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "video_analysis_failed",
                    video_id=video_configs[i]["video_id"],
                    error=str(result),
                )
                analysis_results.append(
                    {
                        "video_id": video_configs[i]["video_id"],
                        "status": "failed",
                        "error": str(result),
                    }
                )
            else:
                analysis_results.append(result)

        logger.info(
            "batch_analysis_completed",
            total=len(video_configs),
            success=len([r for r in analysis_results if r.get("status") != "failed"]),
        )

        return analysis_results

    async def _analyze_single_video_with_id(
        self,
        video_id: str,
        video_path: str,
        audio_url: Optional[str],
        enable_speech_recognition: bool,
    ) -> Dict[str, Any]:
        """分析单个视频并包含ID"""
        result = await self.analyze_full_content(
            video_path=video_path,
            audio_url=audio_url,
            enable_speech_recognition=enable_speech_recognition,
        )
        result["video_id"] = video_id
        return result

    async def _fuse_audio_visual_analysis(
        self, visual_analysis: str, transcript_text: str
    ) -> str:
        """
        融合音视频分析结果

        Args:
            visual_analysis: 视觉分析文本
            transcript_text: 语音转写文本

        Returns:
            融合分析结果
        """
        prompt = AudioTranscriptPrompts.AUDIO_VISUAL_FUSION.format(
            visual_analysis=visual_analysis, transcript=transcript_text
        )

        try:
            fusion_result = await self.dashscope_client.chat(prompt)
            return fusion_result
        except Exception as e:
            logger.error("fusion_analysis_failed", error=str(e))
            raise LLMServiceError(f"音视频融合分析失败: {str(e)}")

    async def extract_audio_for_recognition(
        self, video_path: str, output_path: str
    ) -> str:
        """
        从视频中提取音频用于识别

        Args:
            video_path: 视频文件路径
            output_path: 输出音频文件路径

        Returns:
            音频文件路径

        注意：此方法仅提取音频，实际使用时需要将音频上传到公网URL
        """
        import ffmpeg

        try:
            logger.info("extracting_audio", video_path=video_path)

            # 使用FFmpeg提取音频
            stream = ffmpeg.input(video_path)
            stream = ffmpeg.output(
                stream,
                output_path,
                acodec="pcm_s16le",  # 16位PCM
                ar=16000,  # 16kHz采样率
                ac=1,  # 单声道
            )
            ffmpeg.run(stream, overwrite_output=True, quiet=True)

            logger.info("audio_extracted", output_path=output_path)
            return output_path

        except Exception as e:
            logger.error("audio_extraction_failed", error=str(e))
            raise AnalysisError(f"音频提取失败: {str(e)}")

    def format_analysis_for_llm(self, analysis_result: Dict[str, Any]) -> str:
        """
        格式化分析结果用于LLM Pass 1输入

        Args:
            analysis_result: 完整分析结果

        Returns:
            格式化的文本
        """
        formatted_parts = []

        # 视觉分析
        if analysis_result.get("visual_analysis"):
            formatted_parts.append("【视觉内容】")
            formatted_parts.append(analysis_result["visual_analysis"])

        # 语音内容
        if analysis_result.get("has_speech") and analysis_result.get("transcript"):
            formatted_parts.append("\n【语音内容】")

            # 使用格式化的转写文本（带时间戳）
            formatted_transcript = self.paraformer_client.format_transcript_for_llm(
                analysis_result["transcript"]
            )
            formatted_parts.append(formatted_transcript)

        # 融合分析
        if analysis_result.get("fusion_analysis"):
            formatted_parts.append("\n【综合分析】")
            formatted_parts.append(analysis_result["fusion_analysis"])

        return "\n".join(formatted_parts)
