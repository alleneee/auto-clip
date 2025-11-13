"""
VideoEditing Tools - 使用@tool装饰器实现（简洁版）

这是另一种实现方式：使用@tool装饰器而不是Toolkit类
适用于不需要复杂工具组织的场景

使用方式：
    from app.tools.video_editing_decorators import extract_video_clip, concatenate_video_clips

    agent = Agent(
        tools=[extract_video_clip, concatenate_video_clips],
        markdown=True
    )
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from agno.tools import tool
from agno.utils.log import log_debug

from app.utils.video_utils import (
    extract_video_clip as _extract_video_clip,
    concatenate_video_clips as _concatenate_video_clips,
    get_video_info as _get_video_info
)
from app.config import settings


@tool(show_result=True)
def extract_video_clip_tool(
    video_path: str,
    start_time: float,
    end_time: float,
    output_path: Optional[str] = None
) -> str:
    """
    提取视频片段（MoviePy 2.x API）

    Args:
        video_path: 源视频路径
        start_time: 开始时间（秒）
        end_time: 结束时间（秒）
        output_path: 输出路径（可选）

    Returns:
        JSON字符串包含成功状态、输出路径、时长等信息
    """
    try:
        if not os.path.exists(video_path):
            result = {
                "success": False,
                "error": f"源视频不存在: {video_path}"
            }
            log_debug(f"extract_video_clip_tool失败: {result['error']}")
            return json.dumps(result)

        if start_time >= end_time:
            result = {
                "success": False,
                "error": f"无效的时间范围: {start_time} >= {end_time}"
            }
            log_debug(f"extract_video_clip_tool失败: {result['error']}")
            return json.dumps(result)

        # 生成输出路径
        temp_dir = settings.temp_dir
        if output_path is None:
            base_name = Path(video_path).stem
            output_path = os.path.join(
                temp_dir,
                f"{base_name}_clip_{start_time:.1f}_{end_time:.1f}.mp4"
            )

        # 提取片段
        result_path = _extract_video_clip(
            video_path=video_path,
            start_time=start_time,
            end_time=end_time,
            output_path=output_path,
            codec=settings.OUTPUT_VIDEO_CODEC,
            audio_codec=settings.OUTPUT_AUDIO_CODEC
        )

        duration = end_time - start_time

        result = {
            "success": True,
            "output_path": result_path,
            "duration": duration,
            "start_time": start_time,
            "end_time": end_time
        }

        log_debug(f"提取视频片段成功: {video_path} [{start_time:.1f}s-{end_time:.1f}s]")
        return json.dumps(result)

    except Exception as e:
        error_msg = f"提取视频片段失败: {str(e)}"
        log_debug(error_msg)
        return json.dumps({
            "success": False,
            "error": error_msg
        })


@tool(show_result=True)
def concatenate_video_clips_tool(
    clip_paths: List[str],
    output_path: str,
    add_transitions: bool = False,
    transition_duration: float = 0.5
) -> str:
    """
    拼接多个视频片段（支持专业转场效果）

    Args:
        clip_paths: 视频片段路径列表
        output_path: 输出路径
        add_transitions: 是否添加转场效果（淡入淡出）
        transition_duration: 转场时长（秒）

    Returns:
        JSON字符串包含成功状态、输出路径、总时长等信息
    """
    try:
        if not clip_paths:
            result = {"success": False, "error": "视频片段列表为空"}
            log_debug(f"concatenate_video_clips_tool失败: {result['error']}")
            return json.dumps(result)

        # 验证所有片段文件存在
        for path in clip_paths:
            if not os.path.exists(path):
                result = {"success": False, "error": f"视频片段不存在: {path}"}
                log_debug(f"concatenate_video_clips_tool失败: {result['error']}")
                return json.dumps(result)

        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 如果需要转场效果
        if add_transitions:
            from moviepy import VideoFileClip, concatenate_videoclips, vfx

            clips = [VideoFileClip(path) for path in clip_paths]

            # 添加转场效果
            clips_with_transitions = []
            for i, clip in enumerate(clips):
                if i == 0:
                    clip = clip.with_effects([vfx.FadeIn(transition_duration)])
                elif i == len(clips) - 1:
                    clip = clip.with_effects([vfx.FadeOut(transition_duration)])
                else:
                    clip = clip.with_effects([
                        vfx.FadeIn(transition_duration),
                        vfx.FadeOut(transition_duration)
                    ])
                clips_with_transitions.append(clip)

            # 拼接
            final_clip = concatenate_videoclips(clips_with_transitions, method="compose")
            final_clip.write_videofile(
                output_path,
                codec=settings.OUTPUT_VIDEO_CODEC,
                audio_codec=settings.OUTPUT_AUDIO_CODEC
            )

            total_duration = final_clip.duration

            # 清理
            for clip in clips:
                clip.close()
            final_clip.close()
        else:
            # 简单拼接
            result_path = _concatenate_video_clips(
                clip_paths=clip_paths,
                output_path=output_path,
                method="compose",
                codec=settings.OUTPUT_VIDEO_CODEC,
                audio_codec=settings.OUTPUT_AUDIO_CODEC
            )

            info = _get_video_info(result_path)
            total_duration = info['duration']

        # 计算文件大小
        file_size = os.path.getsize(output_path)
        file_size_mb = file_size / (1024 * 1024)

        result = {
            "success": True,
            "output_path": output_path,
            "total_duration": total_duration,
            "clip_count": len(clip_paths),
            "file_size_mb": file_size_mb,
            "transitions_applied": add_transitions
        }

        log_debug(f"拼接{len(clip_paths)}个视频成功: {output_path}")
        return json.dumps(result)

    except Exception as e:
        error_msg = f"拼接视频失败: {str(e)}"
        log_debug(error_msg)
        return json.dumps({
            "success": False,
            "error": error_msg
        })


@tool(show_result=True)
def get_video_metadata(video_path: str) -> str:
    """
    获取视频元数据信息

    Args:
        video_path: 视频文件路径

    Returns:
        JSON字符串包含时长、分辨率、帧率等信息
    """
    try:
        if not os.path.exists(video_path):
            result = {
                "success": False,
                "error": f"视频文件不存在: {video_path}"
            }
            log_debug(f"get_video_metadata失败: {result['error']}")
            return json.dumps(result)

        # 获取视频元数据
        info = _get_video_info(video_path)

        # 添加文件大小
        file_size = os.path.getsize(video_path)
        info['file_size_mb'] = file_size / (1024 * 1024)
        info['success'] = True

        log_debug(f"获取视频信息成功: {video_path}")
        return json.dumps(info)

    except Exception as e:
        error_msg = f"获取视频信息失败: {str(e)}"
        log_debug(error_msg)
        return json.dumps({
            "success": False,
            "error": error_msg
        })


# 便捷导出
__all__ = [
    "extract_video_clip_tool",
    "concatenate_video_clips_tool",
    "get_video_metadata"
]
