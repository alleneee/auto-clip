"""
ContentAnalyzerAgent - 全模态内容分析专家

支持多种模型：
- DashScope qwen-vl-plus (默认)
- Gemini via OpenAI-compatible API (代理访问)
输出音视频对齐的结构化数据
"""

import json
import os
from typing import Dict, Any, Optional, Literal
from pathlib import Path
from agno.agent import Agent
from agno.models.dashscope import DashScope
from agno.models.openai.like import OpenAILike
from agno.media import Video

from app.models.agno_models import (
    MultimodalAnalysis,
    TimelineSegment,
    KeyMoment,
    Transcription,
    AudioLayers,
    EmotionType,
    SyncQuality,
    SyncType
)
from app.utils.video_utils import get_video_info
import structlog

logger = structlog.get_logger(__name__)


class ContentAnalyzerAgent:
    """
    全模态内容分析专家Agent

    职责：
    - 使用多模态模型分析视频（DashScope 或 Gemini）
    - 提取音视频对齐的时间轴数据
    - 识别关键时刻和高潮点
    - 转录语音内容（如果有）
    """

    def __init__(
        self,
        model: str = "gemini-2.0-flash",
        api_key: Optional[str] = None,
        temperature: float = 0.3,
        provider: Literal["dashscope", "gemini-proxy"] = None,
        base_url: Optional[str] = None
    ):
        """
        初始化内容分析Agent

        Args:
            model: 模型名称
                - DashScope: "qwen-vl-plus", "qwen-vl-max"
                - Gemini: "gemini-2.0-flash", "gemini-1.5-pro"
            api_key: API密钥（可选，默认从环境变量读取）
            temperature: 温度参数（分析任务建议0.2-0.4）
            provider: 提供商类型
                - "dashscope": 使用阿里云 DashScope
                - "gemini-proxy": 使用 Gemini OpenAI-compatible API
            base_url: API基础URL（仅用于 gemini-proxy）
        """
        self.model_name = model
        self.provider = provider

        # 根据 provider 创建不同的模型实例
        if provider == "gemini-proxy":
            raw_base_url = base_url or os.getenv("GEMINI_BASE_URL")
            if raw_base_url and raw_base_url.endswith("/chat/completions"):
                raw_base_url = raw_base_url.rsplit("/chat/completions", 1)[0]

            model_instance = OpenAILike(
                id="gemini-2.0-flash-exp",
                api_key=api_key or os.getenv("GOOGLE_API_KEY"),
                base_url=raw_base_url,
                temperature=temperature
            )
            logger.info(
                "使用 Gemini OpenAI-compatible API",
                model="gemini-2.0-flash-exp",
                base_url=base_url or os.getenv("GEMINI_BASE_URL")
            )
        elif provider == "gemini":
            from agno.models.google import Gemini
            model_instance = Gemini(
                id=model,
                api_key=api_key or os.getenv("GOOGLE_API_KEY"),
                temperature=temperature
            )
            logger.info("使用 Gemini API", model=model)
        else:
            from app.config import settings
            model_instance = DashScope(
                id=model,
                api_key=api_key or settings.DASHSCOPE_API_KEY,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                temperature=temperature
            )
            logger.info("使用 DashScope API", model=model)

        # 创建Agno Agent
        self.agent = Agent(
            name="ContentAnalyzer",
            model=model_instance,
            description="全模态视频内容分析专家，提取音视频对齐的结构化数据",
            instructions=[
                "你是专业的视频内容分析专家，精通音视频同步分析",
                "分析视频时，必须关注音画对齐：什么画面配合什么声音",
                "识别关键时刻：视觉高潮点、音频高潮点、音画同步的强调点",
                "如果有语音，准确转录并标注时间戳",
                "输出必须是严格的JSON格式，符合MultimodalAnalysis数据模型",
                "重要性评分（1-10）要客观：考虑视觉冲击力、音频强度、情绪变化",
                "音视频同步质量评估：high=完美配合，medium=基本同步，low=不同步"
            ],
            markdown=False
        )

        logger.info(
            "ContentAnalyzerAgent初始化",
            model=model,
            temperature=temperature,
            provider=provider
        )

    def _build_analysis_prompt(self, video_path: str, video_id: str) -> str:
        """
        构建分析提示词

        Args:
            video_path: 视频路径
            video_id: 视频ID

        Returns:
            完整的分析提示词
        """
        # 获取视频元数据
        try:
            video_info = get_video_info(video_path)
            duration = video_info.get('duration')
            resolution = f"{video_info.get('width')}x{video_info.get('height')}"
            fps = video_info.get('fps')
        except Exception as e:
            logger.warning(f"获取视频元数据失败: {e}")
            duration = None
            resolution = None
            fps = None

        prompt = f"""
请对这个视频进行全面的音视频对齐分析。

**视频信息**：
- 视频ID: {video_id}
- 时长: {duration}秒（如已知）
- 分辨率: {resolution or '未知'}

**分析要求**：

1. **时间轴分析**（timeline）：
   - 将视频分成有意义的片段（每段5-30秒）
   - **重要约束**：所有片段的时间范围必须覆盖整个视频，即：
     * 第一个片段的 start 必须是 0.0
     * 最后一个片段的 end 必须等于视频总时长 duration
     * 片段之间不能有时间间隙（前一段的end = 后一段的start）
     * 所有片段的时长总和 = 视频总时长 duration
   - 每段必须包含：
     * start, end: 精确时间戳（秒）
     * visual: 视觉内容描述（场景、动作、镜头）
     * audio: 音频内容描述（语音、音乐、音效）
     * emotion: 情绪类型（**必须**严格使用以下之一：excited/calm/tense/happy/sad/neutral）
     * importance: 重要性评分1-10
     * sync_quality: 音画同步质量（high/medium/low）

2. **关键时刻识别**（key_moments）：
   - 找出3-5个最值得剪辑的时刻
   - 每个时刻标注：
     * timestamp: 精确时间戳
     * visual_peak: 是否为视觉高潮
     * audio_peak: 是否为音频高潮
     * sync_type: 类型（emphasis强调/transition转折/climax高潮/intro介绍/outro结束）
     * description: 详细描述
     * clip_potential: 剪辑潜力0-1

3. **语音转录**（transcription）：
   - 如果有人声对话或旁白，逐句转录
   - 标注每句话的start/end时间和text内容
   - 没有语音则返回null

4. **音频层次**（audio_layers）：
   - speech_segments: 有语音的时间段 [[start, end], ...]
   - music_segments: 有背景音乐的时间段
   - silence_segments: 静音时间段
   - dominant_layer: **严格限定为**以下三个值之一：
     * "speech" - 语音占主导
     * "music" - 音乐占主导
     * "silence" - 静音占主导
     **禁止使用任何其他值**（如sound_effect、sound_effects、sfx、ambient等都是非法的）

**输出格式**（严格JSON）：
```json
{{
  "video_id": "{video_id}",
  "duration": 视频总时长,
  "timeline": [
    {{
      "start": 0.0,
      "end": 15.0,
      "visual": "办公室场景，人物坐在电脑前",
      "audio": "轻柔的背景音乐，无语音",
      "emotion": "calm",
      "importance": 3,
      "sync_quality": "medium"
    }},
    ...
  ],
  "key_moments": [
    {{
      "timestamp": 25.5,
      "visual_peak": true,
      "audio_peak": true,
      "sync_type": "emphasis",
      "description": "特写镜头配合强调语气",
      "clip_potential": 0.95
    }},
    ...
  ],
  "transcription": [
    {{
      "start": 10.0,
      "end": 15.0,
      "text": "这个方法可以节省50%的时间",
      "confidence": 0.95
    }},
    ...
  ],
  "audio_layers": {{
    "speech_segments": [[10, 30], [45, 60]],
    "music_segments": [[0, 10], [60, 90]],
    "silence_segments": [],
    "dominant_layer": "speech"
  }},
  "resolution": "{resolution or '1920x1080'}",
  "fps": {fps or 30}
}}
```

**重要约束**：
1. 只返回JSON，不要有任何其他文字
2. **timeline片段必须覆盖整个视频时长**：
   - 第一个片段从0.0开始，最后一个片段在duration结束
   - 片段之间连续无间隙（前一段end = 后一段start）
   - 所有片段时长总和必须等于视频总时长duration
   - ❌ 错误示例：视频60秒，但timeline只覆盖了0-45秒（缺少45-60秒）
   - ✅ 正确示例：视频60秒，timeline从0.0到60.0连续覆盖
3. emotion字段**必须且只能**使用这6个值：excited, calm, tense, happy, sad, neutral
   （禁止使用intense, anxious, peaceful等其他词汇）
4. dominant_layer字段**必须且只能**使用这3个值：speech, music, silence
   （禁止使用sound_effect, sound_effects, sfx, ambient等其他词汇）
"""
        return prompt.strip()

    def analyze(
        self,
        video_path: str,
        video_id: Optional[str] = None
    ) -> MultimodalAnalysis:
        """
        分析视频内容

        Args:
            video_path: 视频文件路径
            video_id: 视频ID（可选，默认使用文件名）

        Returns:
            MultimodalAnalysis对象
        """
        # 验证视频路径
        path = Path(video_path)
        if not path.exists():
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        # 生成video_id
        if not video_id:
            from uuid import uuid4
            video_id = f"{path.stem}-{uuid4().hex[:8]}"

        logger.info(
            "开始视频内容分析",
            video_path=str(path),
            video_id=video_id,
            model=self.model_name,
            provider=self.provider
        )

        # 构建提示词
        prompt = self._build_analysis_prompt(str(path), video_id)

        # 为Gemini创建临时文件副本以避免409缓存冲突
        temp_video_path = None
        if self.provider == "gemini":
            import shutil
            import tempfile
            from uuid import uuid4

            # 创建临时文件，使用UUID命名避免Gemini缓存冲突
            temp_dir = Path(tempfile.gettempdir()) / "auto-clip-gemini"
            temp_dir.mkdir(exist_ok=True)

            temp_filename = f"{uuid4().hex}{path.suffix}"
            temp_video_path = temp_dir / temp_filename

            shutil.copy2(path, temp_video_path)
            logger.info(
                "为Gemini创建临时视频副本",
                original=str(path),
                temp=str(temp_video_path)
            )
            video_file_path = temp_video_path
        else:
            video_file_path = path

        try:
            # 统一使用本地文件路径创建 Video 对象
            logger.info(
                f"使用 {self.provider} 分析视频...",
                video_path=str(video_file_path),
                model=self.model_name
            )

            # ✅ 创建 Video 对象（适用于 DashScope 和 OpenAI-like API）
            video = Video(filepath=str(video_file_path.absolute()))

            # 调用Agent分析
            response = self.agent.run(
                prompt,
                videos=[video]
            )

            # 提取响应内容
            content = response.content if hasattr(response, 'content') else str(response)


            logger.info("内容分析Agent响应", content_preview=content)

            # 解析JSON
            analysis_data = self._parse_json_response(content)

            # 验证并转换为Pydantic模型
            analysis = MultimodalAnalysis(**analysis_data)

            logger.info(
                "视频分析完成",
                video_id=video_id,
                timeline_segments=len(analysis.timeline),
                key_moments=len(analysis.key_moments),
                has_transcription=analysis.transcription is not None
            )

            return analysis

        except Exception as e:
            logger.error(
                "视频分析失败",
                video_id=video_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
        finally:
            # 清理Gemini临时文件
            if temp_video_path and temp_video_path.exists():
                try:
                    temp_video_path.unlink()
                    logger.debug("已删除Gemini临时视频文件", path=str(temp_video_path))
                except Exception as cleanup_error:
                    logger.warning(
                        "清理临时文件失败",
                        path=str(temp_video_path),
                        error=str(cleanup_error)
                    )

    def _fix_emotion_values(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        修正非法的emotion和dominant_layer值，映射到最接近的合法值

        emotion合法值: excited, calm, tense, happy, sad, neutral
        dominant_layer合法值: speech, music, silence
        """
        VALID_EMOTIONS = {"excited", "calm", "tense", "happy", "sad", "neutral"}
        VALID_DOMINANT_LAYERS = {"speech", "music", "silence"}

        # emotion映射规则：非法值 -> 最接近的合法值
        EMOTION_MAPPING = {
            "intense": "tense",      # 强烈 -> 紧张
            "anxious": "tense",      # 焦虑 -> 紧张
            "peaceful": "calm",      # 平静 -> 冷静
            "joyful": "happy",       # 快乐 -> 高兴
            "melancholy": "sad",     # 忧郁 -> 悲伤
            "energetic": "excited",  # 充满活力 -> 兴奋
            "relaxed": "calm",       # 放松 -> 冷静
            "nervous": "tense",      # 紧张 -> 紧张
            "cheerful": "happy",     # 欢快 -> 高兴
            "gloomy": "sad",         # 阴郁 -> 悲伤
        }

        # dominant_layer映射规则
        DOMINANT_LAYER_MAPPING = {
            "sound_effect": "music",    # 音效 -> 音乐（非语音音频）
            "sound_effects": "music",   # 音效（复数） -> 音乐
            "sfx": "music",             # SFX缩写 -> 音乐
            "ambient": "music",         # 环境音 -> 音乐
            "noise": "silence",         # 噪音 -> 静音
            "background": "music",      # 背景音 -> 音乐
        }

        # 修正timeline中的emotion值
        if "timeline" in data and isinstance(data["timeline"], list):
            for segment in data["timeline"]:
                if "emotion" in segment:
                    emotion = segment["emotion"]
                    if emotion not in VALID_EMOTIONS:
                        # 尝试映射
                        if emotion in EMOTION_MAPPING:
                            original_emotion = emotion
                            segment["emotion"] = EMOTION_MAPPING[emotion]
                            logger.warning(
                                "自动修正非法emotion值",
                                original=original_emotion,
                                corrected=segment["emotion"]
                            )
                        else:
                            # 未知的非法值，默认使用neutral
                            logger.warning(
                                "未知emotion值，使用默认值",
                                original=emotion,
                                default="neutral"
                            )
                            segment["emotion"] = "neutral"

        # 修正audio_layers中的dominant_layer值
        if "audio_layers" in data and isinstance(data["audio_layers"], dict):
            if "dominant_layer" in data["audio_layers"]:
                dominant_layer = data["audio_layers"]["dominant_layer"]
                if dominant_layer not in VALID_DOMINANT_LAYERS:
                    # 尝试映射
                    if dominant_layer in DOMINANT_LAYER_MAPPING:
                        original_layer = dominant_layer
                        data["audio_layers"]["dominant_layer"] = DOMINANT_LAYER_MAPPING[dominant_layer]
                        logger.warning(
                            "自动修正非法dominant_layer值",
                            original=original_layer,
                            corrected=data["audio_layers"]["dominant_layer"]
                        )
                    else:
                        # 未知的非法值，默认使用music
                        logger.warning(
                            "未知dominant_layer值，使用默认值",
                            original=dominant_layer,
                            default="music"
                        )
                        data["audio_layers"]["dominant_layer"] = "music"

        return data

    def _fix_timeline_coverage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        修正 timeline 片段以确保覆盖整个视频时长

        要求：
        1. 第一个片段从 0.0 开始
        2. 最后一个片段在 duration 结束
        3. 片段之间连续无间隙（前一段 end = 后一段 start）
        4. 所有片段时长总和 = 视频总时长

        Args:
            data: 解析后的 JSON 数据

        Returns:
            修正后的数据
        """
        if "timeline" not in data or not isinstance(data["timeline"], list):
            return data

        timeline = data["timeline"]
        duration = data.get("duration")

        if not duration or len(timeline) == 0:
            return data

        # 按 start_time 排序片段
        timeline.sort(key=lambda seg: seg.get("start", 0))

        # 修正第一个片段的 start 为 0.0
        if timeline[0].get("start", 0) != 0.0:
            logger.warning(
                "修正timeline第一个片段起始时间",
                original_start=timeline[0].get("start"),
                corrected_start=0.0
            )
            timeline[0]["start"] = 0.0

        # 修正片段之间的间隙和连续性
        for i in range(len(timeline) - 1):
            current = timeline[i]
            next_seg = timeline[i + 1]

            # 如果当前片段的 end 和下一片段的 start 不连续，修正
            if abs(current.get("end", 0) - next_seg.get("start", 0)) > 0.1:
                logger.warning(
                    "修正timeline片段间隙",
                    segment_index=i,
                    current_end=current.get("end"),
                    next_start=next_seg.get("start"),
                    corrected_next_start=current.get("end")
                )
                next_seg["start"] = current.get("end", 0)

        # 修正最后一个片段的 end 为 duration
        if abs(timeline[-1].get("end", 0) - duration) > 0.1:
            logger.warning(
                "修正timeline最后片段结束时间",
                original_end=timeline[-1].get("end"),
                corrected_end=duration
            )
            timeline[-1]["end"] = duration

        # 验证总时长
        total_duration = sum(seg.get("end", 0) - seg.get("start", 0) for seg in timeline)
        if abs(total_duration - duration) > 0.5:
            logger.warning(
                "timeline总时长与视频时长不匹配",
                calculated_total=round(total_duration, 1),
                video_duration=duration,
                difference=round(abs(total_duration - duration), 1)
            )

        data["timeline"] = timeline
        return data

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """
        解析Agent返回的JSON响应

        处理常见问题：
        - Markdown代码块包裹
        - 额外的文字说明
        - JSON格式错误
        - 非法的emotion枚举值
        """
        # 去除前后空白
        content = content.strip()

        # 提取JSON（如果被Markdown包裹）
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            content = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            content = content[start:end].strip()

        # 尝试解析JSON
        try:
            data = json.loads(content)
            # 修正非法的emotion值
            data = self._fix_emotion_values(data)
            # 修正timeline覆盖
            data = self._fix_timeline_coverage(data)
            return data
        except json.JSONDecodeError as e:
            logger.error(
                "JSON解析失败",
                error=str(e),
                content_preview=content[:200]
            )
            # 尝试修复常见问题
            content = content.replace("'", '"')  # 单引号改双引号
            content = content.rstrip(',')  # 去除尾随逗号
            try:
                data = json.loads(content)
                logger.info("JSON修复成功")
                # 修正非法的emotion值
                data = self._fix_emotion_values(data)
                # 修正timeline覆盖
                data = self._fix_timeline_coverage(data)
                return data
            except:
                raise ValueError(f"无法解析JSON响应: {e}")
