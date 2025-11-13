"""
Agno智能剪辑Agent系统专用数据模型

定义四个Agent之间传递的数据结构：
- ContentAnalyzerAgent: 全模态视频分析结果
- CreativeStrategistAgent: 创意剪辑策略
- TechnicalPlannerAgent: 可执行的技术方案
- QualityReviewerAgent: 质量评审报告
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal, Dict, Any
from enum import Enum


# ==================== Enums ====================

class EmotionType(str, Enum):
    """情绪类型"""
    EXCITED = "excited"
    CALM = "calm"
    TENSE = "tense"
    HAPPY = "happy"
    SAD = "sad"
    NEUTRAL = "neutral"


class SyncQuality(str, Enum):
    """音视频同步质量"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SyncType(str, Enum):
    """同步类型"""
    EMPHASIS = "emphasis"      # 强调
    TRANSITION = "transition"  # 转折
    CLIMAX = "climax"         # 高潮
    INTRO = "intro"           # 介绍
    OUTRO = "outro"           # 结束


class SegmentRole(str, Enum):
    """片段角色"""
    OPENING = "opening"
    BODY = "body"
    ENDING = "ending"
    TRANSITION = "transition"


class VideoStyle(str, Enum):
    """视频风格"""
    TECH_TUTORIAL = "tech_tutorial"
    ENTERTAINMENT = "entertainment"
    STORY = "story"
    NEWS = "news"
    VLOG = "vlog"
    PRODUCT_DEMO = "product_demo"


# ==================== ContentAnalyzerAgent输出 ====================

class TimelineSegment(BaseModel):
    """音视频对齐的时间轴片段"""
    start: float = Field(..., description="开始时间（秒）", ge=0)
    end: float = Field(..., description="结束时间（秒）", ge=0)
    visual: str = Field(..., description="视觉内容描述")
    audio: str = Field(..., description="音频内容描述")
    emotion: EmotionType = Field(default=EmotionType.NEUTRAL, description="情绪类型")
    importance: int = Field(..., description="重要性评分（1-10）", ge=1, le=10)
    sync_quality: SyncQuality = Field(default=SyncQuality.MEDIUM, description="音视频同步质量")

    @field_validator("end")
    @classmethod
    def validate_time_range(cls, v, info):
        """验证时间范围"""
        if "start" in info.data and v <= info.data["start"]:
            raise ValueError("结束时间必须大于开始时间")
        return v


class KeyMoment(BaseModel):
    """关键时刻"""
    timestamp: float = Field(..., description="时间戳（秒）", ge=0)
    visual_peak: bool = Field(default=False, description="是否为视觉高潮点")
    audio_peak: bool = Field(default=False, description="是否为音频高潮点")
    sync_type: SyncType = Field(..., description="同步类型")
    description: str = Field(..., description="描述")
    clip_potential: float = Field(..., description="剪辑潜力（0-1）", ge=0, le=1)


class Transcription(BaseModel):
    """语音转录"""
    start: float = Field(..., ge=0)
    end: float = Field(..., ge=0)
    text: str = Field(..., description="转录文本")
    confidence: float = Field(default=1.0, ge=0, le=1, description="置信度")


class AudioLayers(BaseModel):
    """音频层次分析"""
    speech_segments: List[List[float]] = Field(default_factory=list, description="语音片段 [[start, end], ...]")
    music_segments: List[List[float]] = Field(default_factory=list, description="音乐片段")
    silence_segments: List[List[float]] = Field(default_factory=list, description="静音片段")
    dominant_layer: Literal["speech", "music", "silence"] = Field(default="speech")


class MultimodalAnalysis(BaseModel):
    """ContentAnalyzerAgent的完整输出"""
    video_id: str = Field(..., description="视频ID")
    duration: float = Field(..., description="视频时长（秒）", gt=0)
    timeline: List[TimelineSegment] = Field(..., description="音视频对齐的时间轴")
    key_moments: List[KeyMoment] = Field(default_factory=list, description="关键时刻列表")
    transcription: Optional[List[Transcription]] = Field(default=None, description="语音转录")
    audio_layers: AudioLayers = Field(default_factory=AudioLayers, description="音频层次")

    # 元数据
    resolution: Optional[str] = Field(default=None, description="分辨率（如1920x1080）")
    fps: Optional[float] = Field(default=None, description="帧率")

    class Config:
        json_schema_extra = {
            "example": {
                "video_id": "uuid-123",
                "duration": 180.5,
                "timeline": [
                    {
                        "start": 0,
                        "end": 15,
                        "visual": "办公室全景",
                        "audio": "背景音乐",
                        "emotion": "calm",
                        "importance": 3,
                        "sync_quality": "medium"
                    }
                ],
                "key_moments": [],
                "audio_layers": {
                    "speech_segments": [[15, 30]],
                    "music_segments": [[0, 15]],
                    "dominant_layer": "speech"
                }
            }
        }


# ==================== CreativeStrategistAgent输出 ====================

class ClipStrategyDetail(BaseModel):
    """剪辑策略详情"""
    duration: float = Field(..., description="时长（秒）", gt=0)
    content: str = Field(..., description="内容描述")
    reason: str = Field(..., description="选择理由")


class AudioConstraints(BaseModel):
    """音频剪辑约束"""
    keep_speech_complete: bool = Field(default=True, description="保持语音完整性")
    avoid_cutting_mid_sentence: bool = Field(default=True, description="避免句子中间切断")
    preserve_music_rhythm: bool = Field(default=False, description="保持音乐节奏")


class CreativeStrategy(BaseModel):
    """CreativeStrategistAgent的输出"""
    recommended_style: VideoStyle = Field(..., description="推荐的视频风格")
    viral_hook: str = Field(..., description="病毒式钩子类型")
    narrative_structure: str = Field(..., description="叙事结构")
    theme: str = Field(..., description="视频主题")

    # 分段策略
    opening_strategy: ClipStrategyDetail = Field(..., description="开场策略")
    body_strategy: ClipStrategyDetail = Field(..., description="主体策略")
    ending_strategy: ClipStrategyDetail = Field(..., description="结尾策略")

    # 约束条件
    audio_constraints: AudioConstraints = Field(default_factory=AudioConstraints)

    # 目标时长
    target_duration: float = Field(..., description="目标总时长（秒）", gt=0)


# ==================== TechnicalPlannerAgent输出 ====================

class TransitionConfig(BaseModel):
    """转场配置"""
    transition_in: Literal["none", "fade", "cut"] = Field(default="fade")
    transition_out: Literal["none", "fade", "cut"] = Field(default="fade")
    fade_duration: float = Field(default=0.5, ge=0, le=2, description="淡入淡出时长（秒）")


class ClipSegment(BaseModel):
    """单个剪辑片段"""
    video_id: str = Field(..., description="源视频ID")
    start_time: float = Field(..., description="开始时间（秒）", ge=0)
    end_time: float = Field(..., description="结束时间（秒）", ge=0)
    duration: float = Field(..., description="片段时长（秒）", gt=0)
    role: SegmentRole = Field(..., description="片段角色")
    audio_intact: bool = Field(default=True, description="音频是否完整保留")
    transitions: TransitionConfig = Field(default_factory=TransitionConfig)
    reason: str = Field(..., description="选择此片段的理由")

    # 可选：语音内容
    speech_content: Optional[str] = Field(default=None, description="包含的语音内容")

    @field_validator("end_time")
    @classmethod
    def validate_end_time(cls, v, info):
        if "start_time" in info.data and v <= info.data["start_time"]:
            raise ValueError("结束时间必须大于开始时间")
        return v

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, v, info):
        if "start_time" in info.data and "end_time" in info.data:
            calculated = info.data["end_time"] - info.data["start_time"]
            if abs(calculated - v) > 0.1:  # 允许0.1秒误差
                raise ValueError(f"duration不匹配：计算值{calculated}，提供值{v}")
        return v


class AudioHandling(BaseModel):
    """音频处理配置"""
    preserve_speech: bool = Field(default=True)
    background_music: Literal["none", "fade_between_segments", "continuous"] = Field(
        default="fade_between_segments"
    )
    volume_normalization: bool = Field(default=True)


class FeasibilityCheck(BaseModel):
    """可行性检查结果"""
    duration_match: float = Field(..., description="时长匹配度（0-1）", ge=0, le=1)
    audio_continuity: Literal["excellent", "good", "fair", "poor"] = Field(
        default="good", description="音频连续性"
    )
    technical_issues: List[str] = Field(default_factory=list, description="技术问题列表")


class TechnicalPlan(BaseModel):
    """TechnicalPlannerAgent的输出"""
    segments: List[ClipSegment] = Field(..., description="剪辑片段列表")
    total_duration: float = Field(..., description="总时长（秒）", gt=0)
    audio_handling: AudioHandling = Field(default_factory=AudioHandling)
    feasibility: FeasibilityCheck = Field(..., description="可行性检查")

    @field_validator("total_duration")
    @classmethod
    def validate_total_duration(cls, v, info):
        """验证总时长是否匹配片段之和"""
        if "segments" in info.data:
            calculated = sum(seg.duration for seg in info.data["segments"])
            if abs(calculated - v) > 0.5:  # 允许0.5秒误差（考虑转场）
                raise ValueError(f"总时长不匹配：片段总和{calculated}，声明值{v}")
        return v


# ==================== QualityReviewerAgent输出 ====================

class QualityDimensions(BaseModel):
    """5维度质量评分"""
    narrative_coherence: float = Field(..., description="叙事连贯性", ge=0, le=10)
    audio_video_sync: float = Field(..., description="音画同步", ge=0, le=10)
    content_coverage: float = Field(..., description="内容覆盖", ge=0, le=10)
    production_quality: float = Field(..., description="制作质量", ge=0, le=10)
    engagement_potential: float = Field(..., description="吸引力", ge=0, le=10)


class ReviewFeedback(BaseModel):
    """评审反馈"""
    strengths: List[str] = Field(default_factory=list, description="优点")
    improvements: List[str] = Field(default_factory=list, description="改进建议")


class QualityReview(BaseModel):
    """QualityReviewerAgent的输出"""
    overall_score: float = Field(..., description="总分（0-10）", ge=0, le=10)
    quality_dimensions: QualityDimensions = Field(..., description="5维度评分")
    pass_review: bool = Field(..., description="是否通过评审")
    feedback: ReviewFeedback = Field(default_factory=ReviewFeedback)
    revision_suggestions: List[str] = Field(default_factory=list, description="修订建议（如不通过）")

    @field_validator("overall_score")
    @classmethod
    def calculate_overall_score(cls, v, info):
        """验证总分是否为5维度平均值"""
        if "quality_dimensions" in info.data:
            dims = info.data["quality_dimensions"]
            avg = (
                dims.narrative_coherence +
                dims.audio_video_sync +
                dims.content_coverage +
                dims.production_quality +
                dims.engagement_potential
            ) / 5
            if abs(avg - v) > 0.1:
                raise ValueError(f"总分不匹配：计算平均值{avg:.1f}，声明值{v}")
        return v


# ==================== 完整的团队输出 ====================

class AgnoClipTeamOutput(BaseModel):
    """AgnoClipTeam的最终输出"""
    # 各Agent的输出
    analyses: List[MultimodalAnalysis] = Field(..., description="所有视频的分析结果")
    strategy: CreativeStrategy = Field(..., description="创意策略")
    technical_plan: TechnicalPlan = Field(..., description="技术方案")
    quality_review: QualityReview = Field(..., description="质量评审")

    # 元数据
    total_input_videos: int = Field(..., ge=1, description="输入视频总数")
    processing_time: Optional[float] = Field(default=None, description="处理耗时（秒）")

    # 迭代改进统计
    iteration_count: Optional[int] = Field(default=1, ge=1, le=10, description="实际迭代次数")
    final_passed: Optional[bool] = Field(default=None, description="最终是否通过质量评审")

    # 视频执行结果（可选，启用enable_video_execution时生成）
    clipped_video_path: Optional[str] = Field(default=None, description="剪辑后视频文件路径（Step 5输出）")
    final_video_path: Optional[str] = Field(default=None, description="最终视频文件路径（Step 8输出，包含口播和字幕）")
    video_duration: Optional[float] = Field(default=None, ge=0, description="最终视频时长（秒）")
    video_file_size_mb: Optional[float] = Field(default=None, ge=0, description="最终视频文件大小（MB）")

    # 脚本和TTS结果（可选，启用narration时生成）
    script: Optional["ScriptGeneration"] = Field(default=None, description="生成的口播脚本（Step 6输出）")
    tts_result: Optional["TTSGenerationResult"] = Field(default=None, description="TTS音频生成结果（Step 7输出）")

    # 字幕文件（可选）
    srt_file_path: Optional[str] = Field(default=None, description="SRT字幕文件路径")

    class Config:
        json_schema_extra = {
            "example": {
                "analyses": [],
                "strategy": {},
                "technical_plan": {},
                "quality_review": {},
                "total_input_videos": 2,
                "processing_time": 45.3
            }
        }


# ==================== ScriptGeneratorAgent输出 ====================

class NarrationSegment(BaseModel):
    """口播文案片段（对应剪辑片段）"""
    segment_index: int = Field(..., description="对应的剪辑片段索引", ge=0)
    start_time: float = Field(..., description="开始时间（秒）", ge=0)
    end_time: float = Field(..., description="结束时间（秒）", ge=0)
    duration: float = Field(..., description="时长（秒）", gt=0)
    text: str = Field(..., description="口播文案文本", min_length=1)
    purpose: str = Field(..., description="该段文案的作用", examples=["开场引入", "解释操作", "总结收尾"])

    @field_validator("end_time")
    @classmethod
    def validate_end_time(cls, v, info):
        if "start_time" in info.data and v <= info.data["start_time"]:
            raise ValueError("结束时间必须大于开始时间")
        return v

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, v, info):
        if "start_time" in info.data and "end_time" in info.data:
            calculated = info.data["end_time"] - info.data["start_time"]
            if abs(calculated - v) > 0.1:
                raise ValueError(f"duration不匹配：计算值{calculated}，提供值{v}")
        return v


class ScriptGeneration(BaseModel):
    """ScriptGeneratorAgent的输出"""
    title: str = Field(..., description="视频标题", min_length=1)
    hook_line: str = Field(..., description="开场钩子文案（前3秒）", min_length=1)
    narration_segments: List[NarrationSegment] = Field(..., description="分段口播文案列表")
    full_script: str = Field(..., description="完整文案（所有片段拼接）", min_length=1)
    word_count: int = Field(..., description="文案总字数", ge=0)
    estimated_speech_duration: float = Field(..., description="预估语音时长（秒）", ge=0)
    style_notes: str = Field(default="", description="文案风格说明")

    # TTS配置
    tts_voice: str = Field(default="longxiaochun", description="TTS语音模型")
    tts_speed: float = Field(default=1.0, ge=0.5, le=2.0, description="语速倍数")

    @field_validator("full_script")
    @classmethod
    def validate_full_script(cls, v, info):
        """验证完整文案是否为各段拼接"""
        if "narration_segments" in info.data:
            segments = info.data["narration_segments"]
            combined = "".join(seg.text for seg in segments)
            # 允许有些许格式差异（空格、换行）
            if combined.replace(" ", "").replace("\n", "") != v.replace(" ", "").replace("\n", ""):
                # 警告而非错误
                pass
        return v


# ==================== TTS生成结果 ====================

class TTSSegmentAudio(BaseModel):
    """单个片段的TTS音频结果"""
    segment_index: int = Field(..., description="片段索引", ge=0)
    start_time: float = Field(..., description="开始时间（秒）", ge=0)
    end_time: float = Field(..., description="结束时间（秒）", ge=0)
    audio_path: str = Field(..., description="音频文件路径")
    duration: float = Field(..., description="实际音频时长（秒）", ge=0)
    text: str = Field(..., description="生成的文本")
    voice: str = Field(..., description="使用的音色")


class TTSGenerationResult(BaseModel):
    """完整的TTS生成结果"""
    segments: List[TTSSegmentAudio] = Field(..., description="各段音频结果")
    total_duration: float = Field(..., description="总音频时长（秒）", ge=0)
    success_count: int = Field(..., description="成功生成的段数", ge=0)
    failed_count: int = Field(default=0, description="失败的段数", ge=0)

    @field_validator("total_duration")
    @classmethod
    def validate_total_duration(cls, v, info):
        if "segments" in info.data:
            calculated = sum(seg.duration for seg in info.data["segments"])
            if abs(calculated - v) > 0.5:
                raise ValueError(f"总时长不匹配：片段总和{calculated}，声明值{v}")
        return v
