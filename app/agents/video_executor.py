"""
VideoExecutorAgent - 视频剪辑执行Agent

将AgnoClipTeam生成的技术方案转化为实际的视频剪辑
使用VideoEditingTools（Agno Toolkit）执行MoviePy 2.x操作
"""

import os
import json
from typing import Dict, Any, List, Optional
from pathlib import Path

from app.tools.video_editing_tool import VideoEditingTools
from app.models.agno_models import TechnicalPlan, MultimodalAnalysis, TTSGenerationResult, ScriptGeneration
from moviepy import VideoFileClip, AudioFileClip, CompositeVideoClip, CompositeAudioClip, TextClip, vfx
import structlog

logger = structlog.get_logger(__name__)


class VideoExecutorAgent:
    """
    视频剪辑执行Agent

    职责：
    - 接收TechnicalPlan（技术方案）
    - 使用VideoEditingTool执行实际剪辑
    - 生成最终视频文件
    - 返回执行结果和统计信息
    """

    def __init__(
        self,
        temp_dir: Optional[str] = None,
        default_add_transitions: bool = True
    ):
        """
        初始化视频执行Agent

        Args:
            temp_dir: 临时文件目录
            default_add_transitions: 默认是否添加转场效果
        """
        self.video_tool = VideoEditingTools(temp_dir=temp_dir)
        self.default_add_transitions = default_add_transitions

        logger.info(
            "VideoExecutorAgent初始化",
            add_transitions=default_add_transitions
        )

    def execute(
        self,
        technical_plan: TechnicalPlan,
        analyses: List[MultimodalAnalysis],
        output_path: str,
        add_transitions: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        执行技术剪辑方案

        Args:
            technical_plan: AgnoClipTeam生成的技术方案
            analyses: 视频分析结果（用于定位源视频）
            output_path: 最终视频输出路径
            add_transitions: 是否添加转场（None=使用默认值）

        Returns:
            Dict包含:
            - success: bool - 是否成功
            - output_path: str - 输出视频路径
            - total_duration: float - 总时长
            - segment_count: int - 片段数量
            - file_size_mb: float - 文件大小
            - execution_details: Dict - 执行详情
            - error: str - 错误信息（失败时）
        """
        if add_transitions is None:
            add_transitions = self.default_add_transitions

        try:
            logger.info(
                "开始执行剪辑方案",
                segments=len(technical_plan.segments),
                videos=len(analyses),
                add_transitions=add_transitions
            )

            # 构建video_id到路径的映射
            video_paths = []
            video_id_map = {}

            for analysis in analyses:
                # 假设video_id是文件路径的stem（在实际使用中需要从分析结果获取原始路径）
                # 这里需要调用者传入完整的视频路径映射
                video_id_map[analysis.video_id] = analysis.video_id
                video_paths.append(analysis.video_id)

            # 转换TechnicalPlan的segments为tool所需格式
            segments_config = []
            for segment in technical_plan.segments:
                segments_config.append({
                    "video_id": segment.video_id,
                    "start_time": segment.start_time,
                    "end_time": segment.end_time,
                    "role": segment.role
                })

            # 调用VideoEditingTools执行剪辑（返回JSON字符串）
            result_json = self.video_tool.execute_clip_plan(
                video_paths=video_paths,
                segments=segments_config,
                output_path=output_path,
                add_transitions=add_transitions
            )

            # 解析JSON结果
            result = json.loads(result_json)

            if not result["success"]:
                logger.error("剪辑执行失败", error=result.get("error"))
                return result

            logger.info(
                "剪辑方案执行成功",
                output_path=result["output_path"],
                total_duration=result["total_duration"],
                file_size_mb=result.get("file_size_mb", 0)
            )

            # 添加执行详情
            result["execution_details"] = {
                "plan_total_duration": technical_plan.total_duration,
                "actual_total_duration": result["total_duration"],
                "duration_match": result["total_duration"] / technical_plan.total_duration if technical_plan.total_duration > 0 else 0,
                "audio_handling": {
                    "preserve_speech": technical_plan.audio_handling.preserve_speech,
                    "background_music": technical_plan.audio_handling.background_music,
                    "volume_normalization": technical_plan.audio_handling.volume_normalization
                },
                "feasibility": {
                    "duration_match": technical_plan.feasibility.duration_match,
                    "audio_continuity": technical_plan.feasibility.audio_continuity,
                    "technical_issues": technical_plan.feasibility.technical_issues
                }
            }

            return result

        except Exception as e:
            error_msg = f"执行剪辑方案失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg
            }

    def execute_from_video_paths(
        self,
        technical_plan: TechnicalPlan,
        video_paths: List[str],
        output_path: str,
        add_transitions: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        从视频路径列表执行剪辑方案（简化版）

        Args:
            technical_plan: 技术方案
            video_paths: 源视频路径列表（与segments中的video_id对应）
            output_path: 输出路径
            add_transitions: 是否添加转场

        Returns:
            执行结果字典
        """
        if add_transitions is None:
            add_transitions = self.default_add_transitions

        try:
            logger.info(
                "开始执行剪辑方案（从路径列表）",
                video_count=len(video_paths),
                segment_count=len(technical_plan.segments)
            )

            # 转换segments为tool格式
            segments_config = []
            for segment in technical_plan.segments:
                segments_config.append({
                    "video_id": segment.video_id,
                    "start_time": segment.start_time,
                    "end_time": segment.end_time,
                    "role": segment.role
                })

            # 执行剪辑（返回JSON字符串）
            result_json = self.video_tool.execute_clip_plan(
                video_paths=video_paths,
                segments=segments_config,
                output_path=output_path,
                add_transitions=add_transitions
            )

            # 解析JSON结果
            result = json.loads(result_json)

            if not result["success"]:
                return result

            # 添加执行详情
            result["execution_details"] = {
                "plan_total_duration": technical_plan.total_duration,
                "actual_total_duration": result["total_duration"],
                "segments_processed": result["segment_count"]
            }

            logger.info(
                "剪辑执行成功",
                output_path=result["output_path"],
                duration=result["total_duration"]
            )

            return result

        except Exception as e:
            error_msg = f"执行剪辑失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg
            }

    def _generate_srt_file(
        self,
        tts_result: TTSGenerationResult,
        output_path: str
    ) -> str:
        """
        生成SRT字幕文件（基于TTS实际音频时长）

        Args:
            tts_result: TTS生成结果（包含实际音频时长）
            output_path: SRT文件输出路径

        Returns:
            生成的SRT文件路径
        """
        def format_srt_time(seconds: float) -> str:
            """将秒数转换为SRT时间格式 HH:MM:SS,mmm"""
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            millis = int((seconds % 1) * 1000)
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

        with open(output_path, 'w', encoding='utf-8') as f:
            for i, tts_seg in enumerate(tts_result.segments, 1):
                start_time = tts_seg.start_time
                end_time = tts_seg.end_time or (start_time + tts_seg.duration)
                if tts_seg.duration:
                    end_time = start_time + tts_seg.duration
                # SRT格式:
                # 1
                # 00:00:00,000 --> 00:00:03,500
                # 字幕文本
                #
                f.write(f"{i}\n")
                f.write(f"{format_srt_time(start_time)} --> {format_srt_time(end_time)}\n")
                f.write(f"{tts_seg.text}\n")
                f.write("\n")

        logger.info("SRT字幕文件已生成（基于TTS实际时长）", output_path=output_path)
        return output_path

    def add_narration_and_subtitles(
        self,
        video_path: str,
        script: ScriptGeneration,
        tts_result: TTSGenerationResult,
        output_path: str,
        subtitle_config: Optional[Dict[str, Any]] = None,
        generate_srt: bool = True,
        burn_subtitles: bool = True
    ) -> Dict[str, Any]:
        """
        为视频添加TTS口播音频和字幕

        关键步骤：
        1. 移除原视频音频（避免音频冲突）
        2. 添加TTS生成的口播音频
        3. 生成SRT字幕文件（可选）
        4. 烧录字幕到视频（可选）

        Args:
            video_path: 已剪辑的视频路径
            script: ScriptGeneratorAgent生成的脚本
            tts_result: TTS音频生成结果
            output_path: 最终输出路径
            subtitle_config: 字幕样式配置（可选,仅烧录字幕时使用）
            generate_srt: 是否生成SRT字幕文件（默认True）
            burn_subtitles: 是否将字幕烧录到视频（默认True）

        Returns:
            Dict包含:
            - success: bool
            - output_path: str
            - total_duration: float
            - has_audio: bool
            - has_subtitles: bool (烧录字幕)
            - srt_path: str (SRT文件路径,如果生成)
            - error: str (失败时)
        """
        try:
            logger.info(
                "开始添加口播和字幕",
                video_path=video_path,
                tts_segments=len(tts_result.segments),
                output_path=output_path,
                generate_srt=generate_srt,
                burn_subtitles=burn_subtitles
            )

            # 结果字典
            result = {
                "success": False
            }

            subtitle_defaults = {
                "fontsize": 48,
                "color": "white",
                "bg_color": "rgba(0,0,0,128)",
                "method": "caption",
                "align": "center",
                "font": [
                    "STHeiti-Medium",
                    "SimHei",
                    "SourceHanSansSC-Regular",
                    "NotoSansCJK-Regular",
                    "Arial Unicode MS"
                ]
            }
            subtitle_config_input = subtitle_config or {}
            normalized_subtitle = dict(subtitle_config_input)
            if "font_size" in normalized_subtitle and "fontsize" not in normalized_subtitle:
                normalized_subtitle["fontsize"] = normalized_subtitle.pop("font_size")
            if "font_color" in normalized_subtitle and "color" not in normalized_subtitle:
                normalized_subtitle["color"] = normalized_subtitle.pop("font_color")
            subtitle_config = {**subtitle_defaults, **normalized_subtitle}

            # 0. 生成SRT字幕文件（如果需要）
            if generate_srt:
                srt_path = str(Path(output_path).with_suffix('.srt'))
                self._generate_srt_file(tts_result, srt_path)
                result["srt_path"] = srt_path
                logger.info("SRT字幕文件已生成", srt_path=srt_path)

            # 1. 加载视频并移除原音频
            video_clip = VideoFileClip(video_path)
            video_without_audio = video_clip.without_audio()

            logger.info(
                "已移除原视频音频",
                original_duration=video_clip.duration,
                had_audio=video_clip.audio is not None
            )

            # 2. 构建TTS音频轨道
            audio_clips = []
            for tts_segment in sorted(tts_result.segments, key=lambda x: x.segment_index):
                audio_clip = AudioFileClip(tts_segment.audio_path)
                # 设置音频在时间轴上的位置
                audio_clip = audio_clip.set_start(tts_segment.start_time)
                audio_clips.append(audio_clip)

            # 创建复合音频（所有TTS片段）
            if audio_clips:
                composite_audio = CompositeAudioClip(audio_clips)
                video_with_audio = video_without_audio.set_audio(composite_audio)
                logger.info(
                    "TTS音频轨道已添加",
                    audio_segments=len(audio_clips),
                    total_audio_duration=tts_result.total_duration
                )
            else:
                video_with_audio = video_without_audio
                logger.warning("没有TTS音频片段，跳过音频添加")

            # 3. 烧录字幕到视频（如果需要）
            # 关键：使用TTS的实际音频时长，而不是脚本的预估时长
            subtitle_clips = []
            if burn_subtitles:
                default_subtitle_config = subtitle_config.copy()
                default_subtitle_config.setdefault("size", (video_clip.w * 0.9, None))

                for tts_seg in tts_result.segments:
                    font_candidates = default_subtitle_config.get("font")
                    if isinstance(font_candidates, str):
                        font_candidates = [font_candidates]
                    font_candidates = [f for f in (font_candidates or []) if f]
                    if not font_candidates:
                        font_candidates = subtitle_defaults["font"]

                    txt_clip = None
                    last_font_error = None
                    for font_name in font_candidates:
                        try:
                            txt_clip = TextClip(
                                text=tts_seg.text,
                                font=font_name,
                                fontsize=default_subtitle_config["fontsize"],
                                color=default_subtitle_config["color"],
                                bg_color=default_subtitle_config["bg_color"],
                                method=default_subtitle_config["method"],
                                align=default_subtitle_config["align"],
                                size=default_subtitle_config["size"]
                            )
                            break
                        except OSError as font_err:
                            last_font_error = font_err
                            continue

                    if txt_clip is None:
                        logger.warning(
                            "字幕字体不可用，跳过字幕烧录",
                            error=str(last_font_error)
                        )
                        subtitle_clips = []
                        burn_subtitles = False
                        break

                    # 设置字幕时间轴（使用TTS的实际时长，确保音画同步）
                    txt_clip = txt_clip.set_start(tts_seg.start_time)
                    txt_clip = txt_clip.set_duration(tts_seg.duration)

                    # 设置字幕位置（底部居中）
                    txt_clip = txt_clip.set_position(("center", "bottom"))

                    subtitle_clips.append(txt_clip)

                logger.info(
                    "字幕烧录准备完成（基于TTS实际时长）",
                    subtitle_count=len(subtitle_clips)
                )

            # 4. 将字幕叠加到视频上
            if subtitle_clips and burn_subtitles:
                final_video = CompositeVideoClip(
                    [video_with_audio] + subtitle_clips
                )
                logger.info("字幕已叠加到视频")
            else:
                final_video = video_with_audio
                if not burn_subtitles:
                    logger.info("不烧录字幕，使用纯视频+音频")

            # 5. 输出最终视频
            final_video.write_videofile(
                output_path,
                codec="libx264",
                audio_codec="aac",
                temp_audiofile="temp-audio.m4a",
                remove_temp=True,
                fps=video_clip.fps
            )

            # 6. 清理资源
            video_clip.close()
            video_without_audio.close()
            if audio_clips:
                for clip in audio_clips:
                    clip.close()
            if subtitle_clips:
                for clip in subtitle_clips:
                    clip.close()
            final_video.close()

            # 7. 验证输出
            output_file = Path(output_path)
            if not output_file.exists():
                raise FileNotFoundError(f"输出文件未生成: {output_path}")

            file_size_mb = output_file.stat().st_size / (1024 * 1024)

            logger.info(
                "口播和字幕添加完成",
                output_path=output_path,
                file_size_mb=f"{file_size_mb:.2f}MB",
                has_srt=generate_srt,
                has_burned_subtitles=burn_subtitles
            )

            result.update({
                "success": True,
                "output_path": output_path,
                "total_duration": video_clip.duration,
                "has_audio": len(audio_clips) > 0,
                "has_burned_subtitles": burn_subtitles and len(subtitle_clips) > 0,
                "file_size_mb": file_size_mb,
                "narration_segments": len(tts_result.segments),
                "subtitle_count": len(subtitle_clips)
            })

            return result

        except Exception as e:
            error_msg = f"添加口播和字幕失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg
            }


# 便捷函数
def create_video_executor(**kwargs) -> VideoExecutorAgent:
    """创建VideoExecutorAgent实例"""
    return VideoExecutorAgent(**kwargs)
