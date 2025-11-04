"""
剪辑决策模型
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ClipDecision(BaseModel):
    """单个剪辑片段决策"""

    video_id: str = Field(..., description="源视频ID")
    start_time: float = Field(..., ge=0, description="开始时间（秒）")
    end_time: float = Field(..., gt=0, description="结束时间（秒）")
    reason: str = Field(..., description="选择理由")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度")
    tags: List[str] = Field(default_factory=list, description="标签")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外信息")

    @property
    def duration(self) -> float:
        """片段时长"""
        return self.end_time - self.start_time

    def validate_times(self):
        """验证时间合法性"""
        if self.end_time <= self.start_time:
            raise ValueError(f"结束时间({self.end_time})必须大于开始时间({self.start_time})")
        return self

    class Config:
        json_schema_extra = {
            "example": {
                "video_id": "vid_abc123",
                "start_time": 10.5,
                "end_time": 25.3,
                "reason": "精彩进球瞬间，情绪高涨",
                "confidence": 0.92,
                "tags": ["highlight", "goal", "excitement"],
                "metadata": {"scene_type": "action", "emotion": "positive"}
            }
        }


class ClipList(BaseModel):
    """完整的剪辑方案"""

    theme: str = Field(..., description="主题/标题")
    description: Optional[str] = Field(None, description="描述")
    clips: List[ClipDecision] = Field(..., min_items=1, description="剪辑片段列表")
    total_duration: float = Field(..., gt=0, description="总时长（秒）")
    target_duration: Optional[float] = Field(None, description="目标时长")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")

    @property
    def clip_count(self) -> int:
        """片段数量"""
        return len(self.clips)

    @property
    def average_confidence(self) -> float:
        """平均置信度"""
        if not self.clips:
            return 0.0
        return sum(clip.confidence for clip in self.clips) / len(self.clips)

    def sort_by_confidence(self) -> "ClipList":
        """按置信度排序"""
        self.clips.sort(key=lambda x: x.confidence, reverse=True)
        return self

    def sort_by_time(self) -> "ClipList":
        """按时间顺序排序"""
        self.clips.sort(key=lambda x: (x.video_id, x.start_time))
        return self

    class Config:
        json_schema_extra = {
            "example": {
                "theme": "足球比赛精彩集锦",
                "description": "2024赛季最精彩的5个进球瞬间",
                "clips": [
                    {
                        "video_id": "vid_abc123",
                        "start_time": 10.5,
                        "end_time": 25.3,
                        "reason": "精彩进球",
                        "confidence": 0.92,
                        "tags": ["goal"],
                        "metadata": {}
                    }
                ],
                "total_duration": 74.8,
                "target_duration": 60.0,
                "metadata": {"sport": "football", "year": 2024}
            }
        }


class AnalysisResult(BaseModel):
    """视频分析结果（LLM Pass 1输出）"""

    video_id: str = Field(..., description="视频ID")
    visual_analysis: str = Field(..., description="视觉内容分析")
    transcript: Optional[str] = Field(None, description="语音转文字")
    key_moments: List[Dict[str, Any]] = Field(default_factory=list, description="关键时刻")
    emotions: List[str] = Field(default_factory=list, description="情感标签")
    scenes: List[Dict[str, Any]] = Field(default_factory=list, description="场景列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="其他信息")

    class Config:
        json_schema_extra = {
            "example": {
                "video_id": "vid_abc123",
                "visual_analysis": "视频展示了一场激烈的足球比赛，包含多个进球和精彩瞬间...",
                "transcript": "解说员: 球传出去了，射门！球进了！",
                "key_moments": [
                    {"timestamp": 15.2, "description": "进球瞬间", "importance": 0.95}
                ],
                "emotions": ["excitement", "joy", "tension"],
                "scenes": [
                    {"start": 0, "end": 30, "type": "game_play", "intensity": "high"}
                ],
                "metadata": {"language": "zh-CN"}
            }
        }


class ThemeGeneration(BaseModel):
    """主题生成结果（LLM Pass 1综合输出）"""

    theme: str = Field(..., description="生成的主题")
    summary: str = Field(..., description="整体摘要")
    analysis_results: List[AnalysisResult] = Field(..., description="各视频分析结果")
    suggested_style: Optional[str] = Field(None, description="建议的剪辑风格")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")

    class Config:
        json_schema_extra = {
            "example": {
                "theme": "2024赛季足球精彩瞬间",
                "summary": "本视频汇集了本赛季最激动人心的5个进球和防守瞬间",
                "analysis_results": [],
                "suggested_style": "dynamic",
                "metadata": {"total_videos": 3, "avg_duration": 120}
            }
        }
