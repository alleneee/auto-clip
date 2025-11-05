"""
视频处理底层工具函数 - 解耦业务逻辑
提供纯粹的视频操作功能，不包含业务状态管理

设计理念：
- 使用MoviePy统一视频处理，保持技术栈一致性
- 按需提供元数据，避免过度设计
- 纯函数设计，无副作用
"""
import os
import subprocess
import base64
from typing import Dict, Any, Optional, Tuple, List
from moviepy import VideoFileClip, concatenate_videoclips

from app.utils.logger import get_logger

logger = get_logger(__name__)


# ============================================
# 视频基本信息获取
# ============================================

def get_video_info(video_path: str) -> Dict[str, Any]:
    """
    使用MoviePy获取视频基本信息（轻量级，按需使用）

    Args:
        video_path: 视频文件路径

    Returns:
        包含视频基本信息的字典

    Raises:
        FileNotFoundError: 视频文件不存在
        RuntimeError: 获取信息失败

    使用场景：
        - 压缩前后对比（大小、时长）
        - 时长验证
        - 分辨率检查
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频文件不存在: {video_path}")

    try:
        with VideoFileClip(video_path) as clip:
            # 获取文件大小
            file_size = os.path.getsize(video_path)

            info = {
                'duration': clip.duration,          # 时长（秒）
                'width': clip.w,                    # 宽度
                'height': clip.h,                   # 高度
                'fps': clip.fps,                    # 帧率
                'size_bytes': file_size,            # 文件大小（字节）
                'size_mb': file_size / (1024 * 1024),  # 文件大小（MB）
            }

        return info

    except Exception as e:
        raise RuntimeError(f"获取视频信息失败: {str(e)}")


# ============================================
# 视频压缩
# ============================================

def compress_video(
    input_path: str,
    output_path: str,
    target_bitrate: str = "1000k",
    target_resolution: Optional[Tuple[int, int]] = None,
    ffmpeg_path: str = "ffmpeg",
    crf: int = 23,
    preset: str = "medium"
) -> Dict[str, Any]:
    """
    压缩视频（纯工具函数）

    Args:
        input_path: 输入视频路径
        output_path: 输出视频路径
        target_bitrate: 目标码率（如 "1000k"）
        target_resolution: 目标分辨率（宽, 高），None保持原分辨率
        ffmpeg_path: ffmpeg可执行文件路径
        crf: 质量参数 (0-51, 越小质量越高)
        preset: 编码速度预设

    Returns:
        包含压缩统计信息的字典

    Raises:
        FileNotFoundError: 输入文件不存在
        RuntimeError: 压缩失败
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"输入视频不存在: {input_path}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 获取原始视频信息
    original_info = get_video_info(input_path)

    # 构建ffmpeg命令
    cmd = [
        ffmpeg_path,
        '-i', input_path,
        '-c:v', 'libx264',
        '-crf', str(crf),
        '-preset', preset,
        '-b:v', target_bitrate,
        '-c:a', 'aac',
        '-b:a', '128k',
    ]

    # 添加分辨率缩放
    if target_resolution:
        cmd.extend(['-vf', f'scale={target_resolution[0]}:{target_resolution[1]}'])

    cmd.extend(['-y', output_path])

    try:
        logger.info(f"开始压缩视频: {input_path} -> {output_path}")
        logger.debug(f"压缩命令: {' '.join(cmd)}")

        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )

        # 获取压缩后视频信息
        compressed_info = get_video_info(output_path)

        # 计算统计信息
        stats = {
            'original_size': original_info['size_bytes'],
            'compressed_size': compressed_info['size_bytes'],
            'compression_ratio': compressed_info['size_bytes'] / original_info['size_bytes'],
            'space_saved': original_info['size_bytes'] - compressed_info['size_bytes'],
            'original_duration': original_info['duration'],
            'compressed_duration': compressed_info['duration'],
        }

        logger.info(
            f"视频压缩完成\n"
            f"  原始大小: {stats['original_size'] / 1024 / 1024:.2f}MB\n"
            f"  压缩后: {stats['compressed_size'] / 1024 / 1024:.2f}MB\n"
            f"  压缩率: {stats['compression_ratio']:.2%}"
        )

        return stats

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"视频压缩失败: {e.stderr}")


# ============================================
# 视频片段提取
# ============================================

def extract_video_clip(
    video_path: str,
    start_time: float,
    end_time: float,
    output_path: str,
    codec: str = "libx264",
    audio_codec: str = "aac"
) -> str:
    """
    从视频提取片段（纯工具函数）

    Args:
        video_path: 源视频路径
        start_time: 开始时间（秒）
        end_time: 结束时间（秒）
        output_path: 输出路径
        codec: 视频编码器
        audio_codec: 音频编码器

    Returns:
        输出文件路径

    Raises:
        FileNotFoundError: 源视频不存在
        ValueError: 时间范围无效
        RuntimeError: 提取失败
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"源视频不存在: {video_path}")

    if start_time >= end_time:
        raise ValueError(f"无效的时间范围: {start_time} >= {end_time}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        with VideoFileClip(video_path) as video:
            # 验证时间范围
            if end_time > video.duration:
                logger.warning(
                    f"结束时间 {end_time}s 超过视频时长 {video.duration}s，"
                    f"调整为 {video.duration}s"
                )
                end_time = video.duration

            # 提取片段
            clip = video.subclipped(start_time, end_time)
            clip.write_videofile(
                output_path,
                codec=codec,
                audio_codec=audio_codec
            )

        logger.info(f"视频片段提取成功: {output_path}")
        return output_path

    except Exception as e:
        raise RuntimeError(f"提取视频片段失败: {str(e)}")


# ============================================
# 视频拼接
# ============================================

def concatenate_video_clips(
    clip_paths: List[str],
    output_path: str,
    method: str = "compose",
    codec: str = "libx264",
    audio_codec: str = "aac"
) -> str:
    """
    拼接多个视频片段（纯工具函数）

    Args:
        clip_paths: 视频片段路径列表
        output_path: 输出路径
        method: 拼接方法 ("compose" 或 "chain")
        codec: 视频编码器
        audio_codec: 音频编码器

    Returns:
        输出文件路径

    Raises:
        ValueError: 片段列表为空
        RuntimeError: 拼接失败
    """
    if not clip_paths:
        raise ValueError("片段列表不能为空")

    for path in clip_paths:
        if not os.path.exists(path):
            raise FileNotFoundError(f"视频片段不存在: {path}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        # 加载所有片段
        clips = [VideoFileClip(path) for path in clip_paths]

        # 拼接
        final_clip = concatenate_videoclips(clips, method=method)

        # 输出
        final_clip.write_videofile(
            output_path,
            codec=codec,
            audio_codec=audio_codec
        )

        # 清理
        for clip in clips:
            clip.close()
        final_clip.close()

        logger.info(f"视频拼接成功: {len(clip_paths)} 个片段 -> {output_path}")
        return output_path

    except Exception as e:
        raise RuntimeError(f"视频拼接失败: {str(e)}")


# ============================================
# 视频转Base64
# ============================================

def video_to_base64(video_path: str) -> str:
    """
    将视频转换为base64编码（纯工具函数）

    Args:
        video_path: 视频文件路径

    Returns:
        base64编码字符串

    Raises:
        FileNotFoundError: 视频文件不存在
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频文件不存在: {video_path}")

    with open(video_path, 'rb') as f:
        video_data = f.read()
        base64_str = base64.b64encode(video_data).decode('utf-8')

    logger.info(f"视频转base64完成: {len(base64_str)} 字符")
    return base64_str
