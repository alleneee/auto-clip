"""
视频分析编排器 - 符合SOLID原则的重构版本

职责: 编排各个服务完成视频内容分析 (单一职责: 协调orchestration)
通过依赖注入接收所有服务 (依赖倒置: 依赖抽象接口)
"""
from typing import Dict, Any, Optional, List
import asyncio
import tempfile
import uuid
from datetime import datetime
import os

from app.core.exceptions import AnalysisError
from app.utils.logger import get_logger
from app.prompts import AudioTranscriptPrompts

logger = get_logger(__name__)


class VideoAnalysisOrchestrator:
    """
    视频分析编排器 (SRP: 单一职责 - 仅负责协调)

    职责:
    - 协调各个服务完成视频分析流程
    - 管理并行任务执行
    - 处理错误和异常
    - 清理临时文件

    不负责:
    - 具体的视频处理逻辑（由专门服务处理）
    - 具体的AI调用逻辑（由适配器处理）
    """

    def __init__(
        self,
        vision_service,         # IVisionAnalysisService
        speech_service,         # ISpeechRecognitionService
        text_service,           # ITextGenerationService
        video_preprocessor,     # VideoPreprocessor
        audio_extractor,        # AudioExtractor
        storage_service         # IStorageService
    ):
        """
        依赖注入 (DIP: 依赖倒置原则)

        Args:
            vision_service: 视觉分析服务
            speech_service: 语音识别服务
            text_service: 文本生成服务
            video_preprocessor: 视频预处理器
            audio_extractor: 音频提取器
            storage_service: 存储服务
        """
        self.vision_service = vision_service
        self.speech_service = speech_service
        self.text_service = text_service
        self.video_preprocessor = video_preprocessor
        self.audio_extractor = audio_extractor
        self.storage_service = storage_service

        logger.info("video_analysis_orchestrator_initialized")

    async def analyze_with_preprocessing(
        self,
        video_path: str,
        enable_speech_recognition: bool = True,
        visual_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        使用预处理流程分析视频（推荐）

        流程:
        1. 视频压缩 + base64编码
        2. 音频提取 + OSS上传（如果启用语音识别）
        3. 并行执行视觉分析和语音识别
        4. 融合分析结果

        Args:
            video_path: 本地视频路径
            enable_speech_recognition: 是否启用语音识别
            visual_prompt: 自定义视觉分析提示词

        Returns:
            分析结果字典
        """
        temp_files = []

        try:
            logger.info(
                "starting_analysis_with_preprocessing",
                video_path=video_path,
                enable_speech=enable_speech_recognition
            )

            # 步骤1: 视频预处理
            (
                compressed_path,
                video_base64,
                compression_ratio,
                preprocessing_temp_files
            ) = await self.video_preprocessor.compress_and_encode(video_path)

            temp_files.extend(preprocessing_temp_files)

            # 步骤2: 音频处理（如果启用）
            audio_url = None
            if enable_speech_recognition:
                audio_url = await self._prepare_audio_for_recognition(
                    video_path, temp_files
                )

            # 步骤3: 并行执行分析
            analysis_result = await self._execute_parallel_analysis(
                video_base64=video_base64,
                audio_url=audio_url,
                enable_speech_recognition=enable_speech_recognition,
                visual_prompt=visual_prompt
            )

            return analysis_result

        except Exception as e:
            logger.error("analysis_with_preprocessing_failed", error=str(e))
            raise AnalysisError(f"视频分析失败: {str(e)}")
        finally:
            # 清理临时文件
            self._cleanup_temp_files(temp_files)

    async def analyze_from_url(
        self,
        video_url: str,
        audio_url: Optional[str] = None,
        enable_speech_recognition: bool = True,
        visual_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        从网络URL分析视频（不需要预处理）

        Args:
            video_url: 视频的网络URL
            audio_url: 音频的网络URL（可选）
            enable_speech_recognition: 是否启用语音识别
            visual_prompt: 自定义视觉分析提示词

        Returns:
            分析结果字典
        """
        try:
            logger.info(
                "starting_analysis_from_url",
                video_url=video_url,
                audio_url=audio_url
            )

            # 并行执行分析
            analysis_result = await self._execute_parallel_analysis(
                video_url=video_url,
                audio_url=audio_url,
                enable_speech_recognition=enable_speech_recognition,
                visual_prompt=visual_prompt
            )

            return analysis_result

        except Exception as e:
            logger.error("analysis_from_url_failed", error=str(e))
            raise AnalysisError(f"URL视频分析失败: {str(e)}")

    async def _prepare_audio_for_recognition(
        self,
        video_path: str,
        temp_files: List[str]
    ) -> str:
        """
        准备音频用于语音识别（提取 + 上传OSS）

        Args:
            video_path: 视频路径
            temp_files: 临时文件列表（用于跟踪清理）

        Returns:
            音频的公网URL
        """
        # 提取音频
        audio_path = tempfile.mktemp(suffix=".wav", prefix="audio_")
        temp_files.append(audio_path)

        logger.info("extracting_audio", output=audio_path)
        await self.audio_extractor.extract_audio(
            video_path=video_path,
            output_path=audio_path
        )

        # 上传到OSS
        oss_path = f"temp/audio/{datetime.now().strftime('%Y%m%d')}/{uuid.uuid4().hex}.wav"

        logger.info("uploading_audio_to_oss", oss_path=oss_path)
        upload_result = await self.storage_service.upload(
            local_path=audio_path,
            remote_path=oss_path,
            content_type="audio/wav"
        )

        audio_url = upload_result["public_url"]
        logger.info("audio_uploaded_to_oss", url=audio_url)

        return audio_url

    async def _execute_parallel_analysis(
        self,
        video_base64: Optional[str] = None,
        video_url: Optional[str] = None,
        audio_url: Optional[str] = None,
        enable_speech_recognition: bool = True,
        visual_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        并行执行视觉分析和语音识别

        Args:
            video_base64: 视频的base64编码（与video_url二选一）
            video_url: 视频的网络URL（与video_base64二选一）
            audio_url: 音频URL
            enable_speech_recognition: 是否启用语音识别
            visual_prompt: 视觉分析提示词

        Returns:
            分析结果字典
        """
        tasks = []

        # 任务1: 视觉分析
        if video_base64:
            logger.info("scheduling_vision_analysis_base64")
            visual_task = self.vision_service.analyze_from_base64(
                video_base64=video_base64,
                prompt=visual_prompt
            )
        elif video_url:
            logger.info("scheduling_vision_analysis_url")
            visual_task = self.vision_service.analyze_from_url(
                video_url=video_url,
                prompt=visual_prompt
            )
        else:
            raise ValueError("必须提供video_base64或video_url")

        tasks.append(("visual", visual_task))

        # 任务2: 语音识别（如果启用）
        if enable_speech_recognition and audio_url:
            logger.info("scheduling_speech_recognition")
            speech_task = self.speech_service.transcribe_from_url(
                audio_url=audio_url,
                language_hints=["zh", "en"]
            )
            tasks.append(("speech", speech_task))

        # 并行执行
        results = await asyncio.gather(
            *[task for _, task in tasks],
            return_exceptions=True
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

        for task_type, result in zip([t[0] for t in tasks], results):
            if isinstance(result, Exception):
                error_msg = str(result)
                logger.error(f"{task_type}_analysis_failed", error=error_msg)
                analysis_result["errors"].append({
                    "type": task_type,
                    "error": error_msg,
                })
                if task_type == "visual":
                    # 视觉分析失败是致命的
                    analysis_result["status"] = "failed"
            else:
                if task_type == "visual":
                    analysis_result["visual_analysis"] = result
                elif task_type == "speech":
                    analysis_result["transcript"] = result
                    analysis_result["transcript_text"] = (
                        self.speech_service.extract_text(result)
                    )
                    analysis_result["has_speech"] = True

        # 如果视觉分析失败，直接返回
        if analysis_result["status"] == "failed":
            logger.error("visual_analysis_failed_critical")
            return analysis_result

        # 融合分析
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
            "parallel_analysis_completed",
            has_visual=analysis_result["visual_analysis"] is not None,
            has_speech=analysis_result["has_speech"],
            has_fusion=analysis_result["fusion_analysis"] is not None,
        )

        return analysis_result

    async def _fuse_audio_visual_analysis(
        self,
        visual_analysis: str,
        transcript_text: str
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
            visual_analysis=visual_analysis,
            transcript=transcript_text
        )

        return await self.text_service.generate(prompt)

    def _cleanup_temp_files(self, temp_files: List[str]) -> None:
        """清理临时文件"""
        if temp_files:
            logger.info("cleaning_up_temp_files", count=len(temp_files))
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                        logger.debug("temp_file_removed", file=temp_file)
                    except Exception as cleanup_error:
                        logger.warning(
                            "temp_file_cleanup_failed",
                            file=temp_file,
                            error=str(cleanup_error)
                        )

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
            formatted_transcript = self.speech_service.format_for_llm(
                analysis_result["transcript"]
            )
            formatted_parts.append(formatted_transcript)

        # 融合分析
        if analysis_result.get("fusion_analysis"):
            formatted_parts.append("\n【综合分析】")
            formatted_parts.append(analysis_result["fusion_analysis"])

        return "\n".join(formatted_parts)
