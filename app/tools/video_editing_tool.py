"""
VideoEditingTools - MoviePy 2.x视频编辑工具（Agno Toolkit实现）

将核心视频编辑功能封装为Agno Toolkit，让Agent能够：
- 提取视频片段
- 拼接多个视频
- 添加转场效果
- 获取视频信息
"""

import os
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path
import json

from agno.tools import Toolkit
from agno.utils.log import log_debug

from app.utils.video_utils import (
    extract_video_clip,
    concatenate_video_clips,
    get_video_info
)
from app.config import settings


class VideoEditingTools(Toolkit):
    """
    MoviePy 2.x视频编辑工具集（Agno Toolkit）

    提供给Agent的视频编辑能力：
    1. extract_clip: 提取视频片段
    2. concatenate_clips: 拼接视频
    3. get_video_info_tool: 获取视频信息
    4. execute_clip_plan: 执行完整剪辑方案
    """

    def __init__(
        self,
        temp_dir: Optional[str] = None,
        include_tools: Optional[List[str]] = None,
        exclude_tools: Optional[List[str]] = None,
        **kwargs
    ):
        """
        初始化视频编辑工具集

        Args:
            temp_dir: 临时文件目录（默认使用settings.temp_dir）
            include_tools: 包含的工具列表（None=全部）
            exclude_tools: 排除的工具列表
            **kwargs: 传递给Toolkit的其他参数
        """
        self.temp_dir = temp_dir or settings.temp_dir
        os.makedirs(self.temp_dir, exist_ok=True)

        # 定义工具列表
        tools: List[Callable] = [
            self.extract_clip,
            self.concatenate_clips,
            self.get_video_info_tool,
            self.execute_clip_plan
        ]

        # 调用父类初始化（自动注册工具）
        super().__init__(
            name="video_editing",
            tools=tools,
            include_tools=include_tools,
            exclude_tools=exclude_tools,
            **kwargs
        )

        log_debug(f"VideoEditingTools初始化完成 - temp_dir: {self.temp_dir}")

    def extract_clip(
        self,
        video_path: str,
        start_time: float,
        end_time: float,
        output_path: Optional[str] = None
    ) -> str:
        """
        提取视频片段（MoviePy 2.x API: subclipped）

        Agent调用示例:
        ```python
        result = extract_clip(
            video_path="/path/to/video.mp4",
            start_time=10.5,
            end_time=25.0
        )
        # 返回JSON: {"success": true, "output_path": "...", "duration": 14.5}
        ```

        Args:
            video_path: 源视频路径
            start_time: 开始时间（秒）
            end_time: 结束时间（秒）
            output_path: 输出路径（可选，默认自动生成）

        Returns:
            JSON字符串包含:
            - success: bool - 是否成功
            - output_path: str - 输出文件路径
            - duration: float - 片段时长
            - error: str - 错误信息（失败时）
        """
        try:
            # 参数验证
            if not os.path.exists(video_path):
                result = {
                    "success": False,
                    "error": f"源视频不存在: {video_path}"
                }
                log_debug(f"extract_clip失败: {result['error']}")
                return json.dumps(result)

            if start_time >= end_time:
                result = {
                    "success": False,
                    "error": f"无效的时间范围: {start_time} >= {end_time}"
                }
                log_debug(f"extract_clip失败: {result['error']}")
                return json.dumps(result)

            # 生成输出路径
            if output_path is None:
                base_name = Path(video_path).stem
                output_path = os.path.join(
                    self.temp_dir,
                    f"{base_name}_clip_{start_time:.1f}_{end_time:.1f}.mp4"
                )

            # 提取片段（使用MoviePy 2.x API）
            result_path = extract_video_clip(
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

            log_debug(f"提取视频片段成功: {video_path} [{start_time:.1f}s-{end_time:.1f}s] -> {result_path}")
            return json.dumps(result)

        except Exception as e:
            error_msg = f"提取视频片段失败: {str(e)}"
            log_debug(error_msg)
            return json.dumps({
                "success": False,
                "error": error_msg
            })

    def concatenate_clips(
        self,
        clip_paths: List[str],
        output_path: str,
        add_transitions: bool = False,
        transition_duration: float = 0.5
    ) -> str:
        """
        拼接多个视频片段（支持专业转场效果）

        Agent调用示例:
        ```python
        result = concatenate_clips(
            clip_paths=["/tmp/clip1.mp4", "/tmp/clip2.mp4"],
            output_path="/output/final.mp4",
            add_transitions=True
        )
        # 返回JSON: {"success": true, "total_duration": 30.5, ...}
        ```

        Args:
            clip_paths: 视频片段路径列表
            output_path: 输出路径
            add_transitions: 是否添加转场效果（淡入淡出）
            transition_duration: 转场时长（秒）

        Returns:
            JSON字符串包含:
            - success: bool - 是否成功
            - output_path: str - 输出文件路径
            - total_duration: float - 总时长
            - clip_count: int - 片段数量
            - file_size_mb: float - 文件大小（MB）
            - transitions_applied: bool - 是否应用了转场
            - error: str - 错误信息（失败时）
        """
        try:
            # 参数验证
            if not clip_paths:
                result = {"success": False, "error": "视频片段列表为空"}
                log_debug(f"concatenate_clips失败: {result['error']}")
                return json.dumps(result)

            # 验证所有片段文件存在
            for path in clip_paths:
                if not os.path.exists(path):
                    result = {"success": False, "error": f"视频片段不存在: {path}"}
                    log_debug(f"concatenate_clips失败: {result['error']}")
                    return json.dumps(result)

            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # 如果需要转场效果
            if add_transitions:
                from moviepy import VideoFileClip, concatenate_videoclips, vfx

                clips = [VideoFileClip(path) for path in clip_paths]

                # 添加转场效果（MoviePy 2.x API: with_effects）
                clips_with_transitions = []
                for i, clip in enumerate(clips):
                    if i == 0:
                        # 第一个片段：淡入
                        clip = clip.with_effects([vfx.FadeIn(transition_duration)])
                    elif i == len(clips) - 1:
                        # 最后一个片段：淡出
                        clip = clip.with_effects([vfx.FadeOut(transition_duration)])
                    else:
                        # 中间片段：淡入+淡出
                        clip = clip.with_effects([
                            vfx.FadeIn(transition_duration),
                            vfx.FadeOut(transition_duration)
                        ])
                    clips_with_transitions.append(clip)

                # 拼接
                final_clip = concatenate_videoclips(clips_with_transitions, method="compose")

                # 写入文件
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
                # 简单拼接（无转场）
                result_path = concatenate_video_clips(
                    clip_paths=clip_paths,
                    output_path=output_path,
                    method="compose",
                    codec=settings.OUTPUT_VIDEO_CODEC,
                    audio_codec=settings.OUTPUT_AUDIO_CODEC
                )

                # 获取总时长
                info = get_video_info(result_path)
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

            log_debug(f"拼接{len(clip_paths)}个视频成功: {output_path} (时长={total_duration:.1f}s, 大小={file_size_mb:.2f}MB)")
            return json.dumps(result)

        except Exception as e:
            error_msg = f"拼接视频失败: {str(e)}"
            log_debug(error_msg)
            return json.dumps({
                "success": False,
                "error": error_msg
            })

    def get_video_info_tool(self, video_path: str) -> str:
        """
        获取视频元数据信息

        Agent调用示例:
        ```python
        info = get_video_info_tool(video_path="/path/to/video.mp4")
        # 返回JSON: {"success": true, "duration": 120.5, "width": 1920, ...}
        ```

        Args:
            video_path: 视频文件路径

        Returns:
            JSON字符串包含:
            - success: bool - 是否成功
            - duration: float - 视频时长（秒）
            - width: int - 宽度
            - height: int - 高度
            - fps: float - 帧率
            - file_size_mb: float - 文件大小（MB）
            - error: str - 错误信息（失败时）
        """
        try:
            if not os.path.exists(video_path):
                result = {
                    "success": False,
                    "error": f"视频文件不存在: {video_path}"
                }
                log_debug(f"get_video_info_tool失败: {result['error']}")
                return json.dumps(result)

            # 获取视频元数据
            info = get_video_info(video_path)

            # 添加文件大小
            file_size = os.path.getsize(video_path)
            info['file_size_mb'] = file_size / (1024 * 1024)
            info['success'] = True

            log_debug(f"获取视频信息成功: {video_path} (时长={info['duration']:.1f}s)")
            return json.dumps(info)

        except Exception as e:
            error_msg = f"获取视频信息失败: {str(e)}"
            log_debug(error_msg)
            return json.dumps({
                "success": False,
                "error": error_msg
            })

    def execute_clip_plan(
        self,
        video_paths: List[str],
        segments: List[Dict[str, Any]],
        output_path: str,
        add_transitions: bool = True
    ) -> str:
        """
        执行完整的剪辑方案（高级编排功能）

        Agent调用示例:
        ```python
        result = execute_clip_plan(
            video_paths=["/videos/video1.mp4", "/videos/video2.mp4"],
            segments=[
                {
                    "video_id": "video1",
                    "start_time": 10.0,
                    "end_time": 20.0,
                    "role": "opening"
                },
                {
                    "video_id": "video2",
                    "start_time": 5.0,
                    "end_time": 15.0,
                    "role": "body"
                }
            ],
            output_path="/output/final.mp4",
            add_transitions=True
        )
        ```

        Args:
            video_paths: 源视频路径列表
            segments: 剪辑片段配置列表
                每个segment包含:
                - video_id: str - 视频ID（对应video_paths索引或文件名）
                - start_time: float - 开始时间
                - end_time: float - 结束时间
                - role: str - 片段角色（opening/body/ending）
            output_path: 最终输出路径
            add_transitions: 是否添加转场

        Returns:
            JSON字符串包含:
            - success: bool - 是否成功
            - output_path: str - 输出文件路径
            - total_duration: float - 总时长
            - segment_count: int - 片段数量
            - file_size_mb: float - 文件大小（MB）
            - error: str - 错误信息（失败时）
        """
        temp_clips = []

        try:
            if not video_paths:
                result = {"success": False, "error": "源视频列表为空"}
                log_debug(f"execute_clip_plan失败: {result['error']}")
                return json.dumps(result)

            if not segments:
                result = {"success": False, "error": "剪辑片段列表为空"}
                log_debug(f"execute_clip_plan失败: {result['error']}")
                return json.dumps(result)

            log_debug(f"开始执行剪辑方案: {len(video_paths)}个视频, {len(segments)}个片段")

            # 创建video_id到路径的映射
            video_map = {}
            for i, path in enumerate(video_paths):
                video_id = Path(path).stem
                video_map[video_id] = path
                video_map[str(i)] = path  # 也支持索引

            # 提取每个片段
            for i, segment in enumerate(segments):
                video_id = segment.get("video_id")
                start_time = segment.get("start_time")
                end_time = segment.get("end_time")

                # 查找源视频（支持带UUID后缀的video_id）
                source_video = None

                # 1. 精确匹配
                if video_id in video_map:
                    source_video = video_map[video_id]
                else:
                    # 2. 尝试移除UUID后缀（格式：filename-uuid）
                    base_id = video_id.split('-')[0] if '-' in video_id else video_id
                    if base_id in video_map:
                        source_video = video_map[base_id]

                if not source_video:
                    result = {
                        "success": False,
                        "error": f"找不到视频ID: {video_id} (尝试了 {video_id} 和 {base_id if '-' in video_id else 'N/A'})"
                    }
                    log_debug(f"execute_clip_plan失败: {result['error']}")
                    return json.dumps(result)

                # 提取片段（调用自己的方法）
                clip_result_json = self.extract_clip(
                    video_path=source_video,
                    start_time=start_time,
                    end_time=end_time
                )

                clip_result = json.loads(clip_result_json)

                if not clip_result["success"]:
                    return clip_result_json  # 返回错误JSON

                temp_clips.append(clip_result["output_path"])

            # 拼接所有片段（调用自己的方法）
            concat_result_json = self.concatenate_clips(
                clip_paths=temp_clips,
                output_path=output_path,
                add_transitions=add_transitions
            )

            concat_result = json.loads(concat_result_json)

            if not concat_result["success"]:
                return concat_result_json

            log_debug(f"剪辑方案执行成功: {output_path} (时长={concat_result['total_duration']:.1f}s)")

            # 返回最终结果
            return json.dumps({
                "success": True,
                "output_path": concat_result["output_path"],
                "total_duration": concat_result["total_duration"],
                "segment_count": len(segments),
                "file_size_mb": concat_result["file_size_mb"],
                "transitions_applied": add_transitions
            })

        except Exception as e:
            error_msg = f"执行剪辑方案失败: {str(e)}"
            log_debug(error_msg)
            return json.dumps({
                "success": False,
                "error": error_msg
            })

        finally:
            # 清理临时片段
            for temp_clip in temp_clips:
                try:
                    if os.path.exists(temp_clip):
                        os.remove(temp_clip)
                        log_debug(f"清理临时片段: {temp_clip}")
                except Exception as e:
                    log_debug(f"清理临时片段失败: {temp_clip} - {str(e)}")


# 单例实例（便捷使用）
video_editing_tool = VideoEditingTools()
