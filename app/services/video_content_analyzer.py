"""
视频内容综合分析服务
集成视觉分析(DashScope)和语音识别(Paraformer)
"""
from typing import Dict, Any, Optional, List, Tuple
import asyncio
import base64
import os
import tempfile

from app.utils.ai_clients.dashscope_client import DashScopeClient
from app.utils.ai_clients.paraformer_client import ParaformerClient
from app.services.video_compression import video_compression_service
from app.utils.oss_client import oss_client
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
        self.compression_service = video_compression_service
        self.oss_client = oss_client

    async def preprocess_video_for_ai(
        self,
        video_path: str,
        enable_speech_recognition: bool = True
    ) -> Tuple[str, Optional[str], List[str]]:
        """
        预处理视频用于AI分析

        处理流程：
        1. 压缩视频（减小大小，优化传输）
        2. 将压缩后的视频转换为base64（用于VL模型）
        3. 如果启用语音识别：提取音频 → 上传OSS → 获取公网URL

        Args:
            video_path: 原始视频文件路径
            enable_speech_recognition: 是否启用语音识别（决定是否处理音频）

        Returns:
            Tuple[str, Optional[str], List[str]]:
                - video_base64: 压缩后视频的base64编码字符串
                - audio_url: 音频的OSS公网URL（如果启用语音识别）
                - temp_files: 需要清理的临时文件列表

        Raises:
            AnalysisError: 预处理失败时抛出
        """
        temp_files = []

        try:
            logger.info(
                "starting_video_preprocessing",
                video_path=video_path,
                enable_speech=enable_speech_recognition
            )

            # 1. 压缩视频
            compressed_video_path = tempfile.mktemp(suffix=".mp4", prefix="compressed_")
            temp_files.append(compressed_video_path)

            logger.info("compressing_video", input=video_path, output=compressed_video_path)
            compressed_path, stats = await self.compression_service.compress_video(
                input_path=video_path,
                output_path=compressed_video_path,
                profile_name="balanced"  # 使用平衡压缩策略
            )

            logger.info(
                "video_compressed",
                compression_ratio=f"{stats['compression_ratio'] * 100:.1f}%",
                original_size_mb=stats['original_size'] / (1024 * 1024),
                compressed_size_mb=stats['compressed_size'] / (1024 * 1024)
            )

            # 2. 转换压缩后视频为base64（用于VL模型）
            logger.info("converting_video_to_base64")
            with open(compressed_path, "rb") as f:
                video_bytes = f.read()
                video_base64 = base64.b64encode(video_bytes).decode('utf-8')

            logger.info(
                "video_base64_ready",
                base64_length=len(video_base64),
                original_bytes=len(video_bytes)
            )

            # 3. 处理音频（如果启用语音识别）
            audio_url = None
            if enable_speech_recognition:
                # 3.1 提取音频
                audio_path = tempfile.mktemp(suffix=".wav", prefix="audio_")
                temp_files.append(audio_path)

                logger.info("extracting_audio", output=audio_path)
                await self.extract_audio_for_recognition(
                    video_path=video_path,
                    output_path=audio_path
                )

                # 3.2 上传音频到OSS
                import uuid
                from datetime import datetime

                # 生成OSS路径：temp/audio/{date}/{uuid}.wav
                oss_path = f"temp/audio/{datetime.now().strftime('%Y%m%d')}/{uuid.uuid4().hex}.wav"

                logger.info("uploading_audio_to_oss", oss_path=oss_path)
                upload_result = await self.oss_client.upload(
                    local_path=audio_path,
                    oss_path=oss_path,
                    content_type="audio/wav"
                )

                audio_url = upload_result["public_url"]
                logger.info("audio_uploaded_to_oss", url=audio_url)

            logger.info(
                "video_preprocessing_completed",
                video_base64_length=len(video_base64),
                audio_url=audio_url,
                temp_files_count=len(temp_files)
            )

            return video_base64, audio_url, temp_files

        except Exception as e:
            logger.error("video_preprocessing_failed", error=str(e))
            # 清理临时文件
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception as cleanup_error:
                        logger.warning("temp_file_cleanup_failed", file=temp_file, error=str(cleanup_error))
            raise AnalysisError(f"视频预处理失败: {str(e)}")

    async def analyze_full_content(
        self,
        video_path: str,
        audio_url: Optional[str] = None,
        enable_speech_recognition: bool = True,
        visual_prompt: Optional[str] = None,
        use_preprocessing: bool = True,
        video_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        完整的视频内容分析（视觉+语音）

        Args:
            video_path: 视频文件本地路径（用于预处理）
            audio_url: 音频文件的公网URL（用于语音识别）
                      如果为None且enable_speech_recognition=True，将自动预处理
            enable_speech_recognition: 是否启用语音识别
            visual_prompt: 自定义视觉分析提示词
            use_preprocessing: 是否使用预处理（压缩+base64转换+音频上传）
                             默认True，使用新流程
            video_url: 视频的网络URL（仅当use_preprocessing=False时使用）
                      用于直接调用analyze_video_visual方法

        Returns:
            包含视觉分析、语音识别和综合分析的字典

        Raises:
            ValueError: 当use_preprocessing=False但未提供video_url时
        """
        temp_files = []

        try:
            logger.info(
                "starting_full_content_analysis",
                video_path=video_path,
                audio_url=audio_url,
                enable_speech=enable_speech_recognition,
                use_preprocessing=use_preprocessing
            )

            # 预处理视频（如果启用）
            if use_preprocessing:
                logger.info("preprocessing_video_for_ai")
                video_base64, preprocessed_audio_url, temp_files = await self.preprocess_video_for_ai(
                    video_path=video_path,
                    enable_speech_recognition=enable_speech_recognition
                )

                # 使用预处理后的音频URL（如果没有提供外部URL）
                if audio_url is None and preprocessed_audio_url:
                    audio_url = preprocessed_audio_url
                    logger.info("using_preprocessed_audio_url", url=audio_url)
            else:
                # 不使用预处理：必须提供video_url
                if not video_url:
                    raise ValueError("use_preprocessing=False时必须提供video_url参数（网络URL）")
                video_base64 = None
                logger.info("skipping_preprocessing_using_network_url", url=video_url)

            # 并行执行视觉分析和语音识别
            tasks = []

            # 任务1：视觉内容分析
            if use_preprocessing and video_base64:
                # 使用base64方式调用VL模型（新方法）
                logger.info("calling_vl_with_base64", base64_length=len(video_base64))
                visual_task = self.dashscope_client.analyze_video_visual_base64(
                    video_base64=video_base64,
                    prompt=visual_prompt
                )
            else:
                # 使用网络URL方式（原有方法）
                logger.info("calling_vl_with_url", url=video_url)
                visual_task = self.dashscope_client.analyze_video_visual(
                    video_url=video_url,
                    prompt=visual_prompt
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

            for task_type, result in zip([t[0] for t in tasks], results):
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
        finally:
            # 清理临时文件
            if temp_files:
                logger.info("cleaning_up_temp_files", count=len(temp_files))
                for temp_file in temp_files:
                    if os.path.exists(temp_file):
                        try:
                            os.remove(temp_file)
                            logger.debug("temp_file_removed", file=temp_file)
                        except Exception as cleanup_error:
                            logger.warning("temp_file_cleanup_failed", file=temp_file, error=str(cleanup_error))

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
        使用MoviePy从视频中提取音频用于语音识别

        提取的音频格式符合Paraformer ASR要求：
        - 采样率：16kHz
        - 声道：单声道
        - 编码：PCM 16位

        Args:
            video_path: 视频文件路径
            output_path: 输出音频文件路径（建议使用.wav格式）

        Returns:
            音频文件路径

        注意：此方法仅提取音频，实际使用时需要将音频上传到公网URL供Paraformer使用

        Raises:
            AnalysisError: 音频提取失败时抛出
        """
        try:
            logger.info("extracting_audio_with_moviepy", video_path=video_path)

            # 使用MoviePy 2.x导入
            from moviepy import VideoFileClip
            import os

            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # 使用MoviePy加载视频并提取音频
            with VideoFileClip(video_path) as video:
                if not video.audio:
                    logger.warning("video_has_no_audio", video_path=video_path)
                    raise AnalysisError(f"视频文件不包含音频轨道: {video_path}")

                # MoviePy 2.x: 提取音频并设置参数
                # write_audiofile 参数：fps=采样率, nbytes=字节数, codec='pcm_s16le'
                video.audio.write_audiofile(
                    output_path,
                    fps=16000,        # 16kHz采样率（Paraformer要求）
                    nbytes=2,         # 16位 = 2字节
                    codec='pcm_s16le', # PCM 16位小端编码
                    ffmpeg_params=["-ac", "1"]  # 单声道
                )

            # 验证输出文件
            if not os.path.exists(output_path):
                raise AnalysisError(f"音频文件提取后未找到: {output_path}")

            file_size = os.path.getsize(output_path)
            logger.info(
                "audio_extracted_successfully",
                output_path=output_path,
                file_size_mb=file_size / (1024 * 1024)
            )

            return output_path

        except AnalysisError:
            raise
        except Exception as e:
            logger.error("audio_extraction_failed", error=str(e), video_path=video_path)
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
