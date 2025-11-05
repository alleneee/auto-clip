"""
音频处理底层工具函数 - 解耦业务逻辑
提供纯粹的音频操作功能，不包含业务状态管理
"""
import os
from typing import Optional
from moviepy import VideoFileClip

from app.utils.logger import get_logger

logger = get_logger(__name__)


# ============================================
# 音频提取
# ============================================

def extract_audio_from_video(
    video_path: str,
    output_path: str,
    audio_codec: str = "mp3",
    bitrate: str = "192k",
    fps: Optional[int] = None,
    nbytes: Optional[int] = None,
    ffmpeg_params: Optional[list] = None
) -> str:
    """
    从视频提取音频（纯工具函数）

    Args:
        video_path: 视频文件路径
        output_path: 输出音频路径
        audio_codec: 音频编码器 (mp3, aac, pcm_s16le等)
        bitrate: 音频码率
        fps: 采样率（如16000用于ASR）
        nbytes: 字节数（如2表示16位）
        ffmpeg_params: 额外的ffmpeg参数（如["-ac", "1"]表示单声道）

    Returns:
        输出音频文件路径

    Raises:
        FileNotFoundError: 视频文件不存在
        RuntimeError: 提取失败
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频文件不存在: {video_path}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        logger.info(f"开始从视频提取音频: {video_path}")

        # 使用MoviePy提取音频
        with VideoFileClip(video_path) as video:
            if video.audio is None:
                raise RuntimeError("视频没有音轨")

            # 构建参数
            kwargs = {
                'codec': audio_codec,
                'bitrate': bitrate
            }

            # 添加可选参数
            if fps is not None:
                kwargs['fps'] = fps
            if nbytes is not None:
                kwargs['nbytes'] = nbytes
            if ffmpeg_params is not None:
                kwargs['ffmpeg_params'] = ffmpeg_params

            # 提取音频并保存
            video.audio.write_audiofile(output_path, **kwargs)

        logger.info(f"音频提取成功: {output_path}")
        return output_path

    except Exception as e:
        raise RuntimeError(f"音频提取失败: {str(e)}")


# ============================================
# 音频转换
# ============================================

def convert_audio_format(
    input_path: str,
    output_path: str,
    target_format: str = "mp3",
    bitrate: str = "192k",
    sample_rate: Optional[int] = None
) -> str:
    """
    转换音频格式（纯工具函数）

    Args:
        input_path: 输入音频路径
        output_path: 输出音频路径
        target_format: 目标格式 (mp3, wav, aac等)
        bitrate: 音频码率
        sample_rate: 采样率 (如 44100, 48000)

    Returns:
        输出音频文件路径

    Raises:
        FileNotFoundError: 输入文件不存在
        RuntimeError: 转换失败
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"输入音频不存在: {input_path}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        from pydub import AudioSegment

        logger.info(f"开始转换音频格式: {input_path} -> {target_format}")

        # 加载音频
        audio = AudioSegment.from_file(input_path)

        # 调整采样率
        if sample_rate:
            audio = audio.set_frame_rate(sample_rate)

        # 导出
        audio.export(
            output_path,
            format=target_format,
            bitrate=bitrate
        )

        logger.info(f"音频格式转换成功: {output_path}")
        return output_path

    except Exception as e:
        raise RuntimeError(f"音频格式转换失败: {str(e)}")


# ============================================
# 音频合并
# ============================================

def merge_audio_files(
    audio_paths: list[str],
    output_path: str,
    format: str = "mp3"
) -> str:
    """
    合并多个音频文件（纯工具函数）

    Args:
        audio_paths: 音频文件路径列表
        output_path: 输出路径
        format: 输出格式

    Returns:
        输出音频文件路径

    Raises:
        ValueError: 音频列表为空
        RuntimeError: 合并失败
    """
    if not audio_paths:
        raise ValueError("音频列表不能为空")

    for path in audio_paths:
        if not os.path.exists(path):
            raise FileNotFoundError(f"音频文件不存在: {path}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        from pydub import AudioSegment

        logger.info(f"开始合并 {len(audio_paths)} 个音频文件")

        # 加载第一个音频
        combined = AudioSegment.from_file(audio_paths[0])

        # 依次追加其他音频
        for path in audio_paths[1:]:
            audio = AudioSegment.from_file(path)
            combined += audio

        # 导出
        combined.export(output_path, format=format)

        logger.info(f"音频合并成功: {output_path}")
        return output_path

    except Exception as e:
        raise RuntimeError(f"音频合并失败: {str(e)}")


# ============================================
# 音频裁剪
# ============================================

def trim_audio(
    audio_path: str,
    output_path: str,
    start_time: float,
    end_time: float,
    format: str = "mp3"
) -> str:
    """
    裁剪音频片段（纯工具函数）

    Args:
        audio_path: 音频文件路径
        output_path: 输出路径
        start_time: 开始时间（秒）
        end_time: 结束时间（秒）
        format: 输出格式

    Returns:
        输出音频文件路径

    Raises:
        FileNotFoundError: 音频文件不存在
        ValueError: 时间范围无效
        RuntimeError: 裁剪失败
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"音频文件不存在: {audio_path}")

    if start_time >= end_time:
        raise ValueError(f"无效的时间范围: {start_time} >= {end_time}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        from pydub import AudioSegment

        logger.info(f"开始裁剪音频: {start_time}s - {end_time}s")

        # 加载音频
        audio = AudioSegment.from_file(audio_path)

        # 裁剪 (pydub使用毫秒)
        start_ms = int(start_time * 1000)
        end_ms = int(end_time * 1000)
        trimmed = audio[start_ms:end_ms]

        # 导出
        trimmed.export(output_path, format=format)

        logger.info(f"音频裁剪成功: {output_path}")
        return output_path

    except Exception as e:
        raise RuntimeError(f"音频裁剪失败: {str(e)}")
