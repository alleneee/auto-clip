"""
阿里云Paraformer语音识别客户端
使用paraformer-v2模型进行异步语音识别
"""
from typing import Optional, List, Dict, Any
import asyncio
import httpx
import json
from http import HTTPStatus
from dashscope.audio.asr import Transcription
import dashscope

from app.config import settings
from app.core.exceptions import LLMServiceError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ParaformerClient:
    """Paraformer异步语音识别客户端"""

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化客户端

        Args:
            api_key: DashScope API密钥，默认从配置读取
        """
        self.api_key = api_key or settings.DASHSCOPE_API_KEY
        dashscope.api_key = self.api_key

    async def transcribe_audio(
        self,
        file_url: str,
        model: str = "paraformer-v2",
        language_hints: Optional[List[str]] = None,
        enable_speaker_diarization: bool = False,
        speaker_count: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        对单个音频文件进行语音识别

        Args:
            file_url: 音频文件的公网URL（HTTP/HTTPS）
            model: 模型名称，默认paraformer-v2
            language_hints: 语言提示列表，如['zh', 'en']
            enable_speaker_diarization: 是否启用说话人分离
            speaker_count: 说话人数量参考值（2-100）

        Returns:
            包含转写文本和详细信息的字典

        Raises:
            LLMServiceError: 识别失败时抛出
        """
        try:
            # 提交异步任务
            logger.info(
                "submitting_paraformer_task",
                file_url=file_url,
                model=model,
                language_hints=language_hints,
            )

            task_params = {
                "model": model,
                "file_urls": [file_url],
            }

            if language_hints:
                task_params["language_hints"] = language_hints

            if enable_speaker_diarization:
                task_params["diarization_enabled"] = True
                if speaker_count:
                    task_params["speaker_count"] = speaker_count

            # 使用asyncio.to_thread在线程池中执行同步调用
            task_response = await asyncio.to_thread(
                Transcription.async_call, **task_params
            )

            if task_response.status_code != HTTPStatus.OK:
                error_msg = f"提交任务失败: {task_response.message}"
                logger.error("paraformer_submit_failed", error=error_msg)
                raise LLMServiceError(error_msg)

            task_id = task_response.output.task_id
            logger.info("paraformer_task_submitted", task_id=task_id)

            # 等待任务完成（使用wait方法同步等待）
            logger.info("waiting_for_paraformer_result", task_id=task_id)

            transcribe_response = await asyncio.to_thread(
                Transcription.wait, task=task_id
            )

            if transcribe_response.status_code != HTTPStatus.OK:
                error_msg = f"获取结果失败: {transcribe_response.message}"
                logger.error("paraformer_fetch_failed", error=error_msg)
                raise LLMServiceError(error_msg)

            # 检查任务状态
            if transcribe_response.output.task_status == "FAILED":
                error_msg = "语音识别任务失败"
                logger.error("paraformer_task_failed", task_id=task_id)
                raise LLMServiceError(error_msg)

            # 获取识别结果
            results = transcribe_response.output.results
            if not results or len(results) == 0:
                error_msg = "无识别结果"
                logger.error("paraformer_no_results", task_id=task_id)
                raise LLMServiceError(error_msg)

            result = results[0]

            # 检查子任务状态
            if result.get("subtask_status") != "SUCCEEDED":
                error_code = result.get("code", "UNKNOWN")
                error_message = result.get("message", "未知错误")
                logger.error(
                    "paraformer_subtask_failed",
                    code=error_code,
                    message=error_message,
                )
                raise LLMServiceError(f"识别失败: {error_message} ({error_code})")

            # 下载识别结果JSON
            transcription_url = result.get("transcription_url")
            if not transcription_url:
                error_msg = "未找到识别结果URL"
                logger.error("paraformer_no_url", task_id=task_id)
                raise LLMServiceError(error_msg)

            logger.info("downloading_transcription_result", url=transcription_url)

            transcription_data = await self._download_transcription(transcription_url)

            logger.info("paraformer_success", file_url=file_url, task_id=task_id)

            return transcription_data

        except LLMServiceError:
            raise
        except Exception as e:
            logger.error("paraformer_exception", error=str(e), file_url=file_url)
            raise LLMServiceError(f"语音识别失败: {str(e)}")

    async def transcribe_multiple(
        self,
        file_urls: List[str],
        model: str = "paraformer-v2",
        language_hints: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        批量识别多个音频文件（异步并行）

        Args:
            file_urls: 音频文件URL列表（最多100个）
            model: 模型名称
            language_hints: 语言提示列表

        Returns:
            识别结果列表

        Raises:
            LLMServiceError: 识别失败时抛出
        """
        if len(file_urls) > 100:
            raise LLMServiceError("单次批量识别最多支持100个文件")

        try:
            logger.info(
                "batch_transcribe_started", file_count=len(file_urls), model=model
            )

            # 提交批量任务
            task_params = {
                "model": model,
                "file_urls": file_urls,
            }

            if language_hints:
                task_params["language_hints"] = language_hints

            task_response = await asyncio.to_thread(
                Transcription.async_call, **task_params
            )

            if task_response.status_code != HTTPStatus.OK:
                error_msg = f"提交批量任务失败: {task_response.message}"
                logger.error("batch_transcribe_submit_failed", error=error_msg)
                raise LLMServiceError(error_msg)

            task_id = task_response.output.task_id
            logger.info("batch_transcribe_submitted", task_id=task_id)

            # 等待所有任务完成
            transcribe_response = await asyncio.to_thread(
                Transcription.wait, task=task_id
            )

            if transcribe_response.status_code != HTTPStatus.OK:
                error_msg = f"获取批量结果失败: {transcribe_response.message}"
                logger.error("batch_transcribe_fetch_failed", error=error_msg)
                raise LLMServiceError(error_msg)

            # 处理每个文件的结果
            results = []
            for result in transcribe_response.output.results:
                if result.get("subtask_status") == "SUCCEEDED":
                    transcription_url = result.get("transcription_url")
                    if transcription_url:
                        try:
                            transcription_data = await self._download_transcription(
                                transcription_url
                            )
                            results.append(transcription_data)
                        except Exception as e:
                            logger.error(
                                "download_transcription_failed",
                                url=result.get("file_url"),
                                error=str(e),
                            )
                            results.append(
                                {"error": str(e), "file_url": result.get("file_url")}
                            )
                else:
                    # 失败的任务
                    logger.warning(
                        "subtask_failed",
                        file_url=result.get("file_url"),
                        code=result.get("code"),
                        message=result.get("message"),
                    )
                    results.append(
                        {
                            "error": result.get("message", "未知错误"),
                            "file_url": result.get("file_url"),
                        }
                    )

            logger.info(
                "batch_transcribe_completed",
                total=len(file_urls),
                succeeded=len([r for r in results if "error" not in r]),
            )

            return results

        except LLMServiceError:
            raise
        except Exception as e:
            logger.error("batch_transcribe_exception", error=str(e))
            raise LLMServiceError(f"批量识别失败: {str(e)}")

    async def _download_transcription(self, url: str) -> Dict[str, Any]:
        """
        下载识别结果JSON

        Args:
            url: 识别结果URL

        Returns:
            识别结果字典

        Raises:
            Exception: 下载或解析失败时抛出
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()

            transcription_data = response.json()

            # 提取关键信息
            result = {
                "file_url": transcription_data.get("file_url"),
                "text": "",  # 完整文本
                "sentences": [],  # 句子列表
                "duration_ms": 0,  # 音频时长（毫秒）
                "properties": transcription_data.get("properties", {}),
            }

            # 提取转写文本
            transcripts = transcription_data.get("transcripts", [])
            if transcripts:
                transcript = transcripts[0]  # 默认使用第一个通道
                result["text"] = transcript.get("text", "")
                result["duration_ms"] = transcript.get(
                    "content_duration_in_milliseconds", 0
                )
                result["sentences"] = transcript.get("sentences", [])

            return result

    def extract_full_text(self, transcription_data: Dict[str, Any]) -> str:
        """
        从识别结果中提取完整文本

        Args:
            transcription_data: 识别结果字典

        Returns:
            完整转写文本
        """
        return transcription_data.get("text", "")

    def extract_sentences_with_timestamps(
        self, transcription_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        提取带时间戳的句子列表

        Args:
            transcription_data: 识别结果字典

        Returns:
            句子列表，每个句子包含text, begin_time, end_time, speaker_id等
        """
        return transcription_data.get("sentences", [])

    def format_transcript_for_llm(self, transcription_data: Dict[str, Any]) -> str:
        """
        格式化转写文本用于LLM输入

        Args:
            transcription_data: 识别结果字典

        Returns:
            格式化后的文本，包含时间戳和说话人信息
        """
        sentences = transcription_data.get("sentences", [])

        if not sentences:
            return transcription_data.get("text", "")

        # 格式化为带时间戳的文本
        formatted_lines = []
        for sentence in sentences:
            begin_time = sentence.get("begin_time", 0) / 1000.0  # 转为秒
            end_time = sentence.get("end_time", 0) / 1000.0
            text = sentence.get("text", "")
            speaker_id = sentence.get("speaker_id")

            if speaker_id is not None:
                formatted_lines.append(
                    f"[{begin_time:.2f}s - {end_time:.2f}s] [说话人{speaker_id}] {text}"
                )
            else:
                formatted_lines.append(f"[{begin_time:.2f}s - {end_time:.2f}s] {text}")

        return "\n".join(formatted_lines)
