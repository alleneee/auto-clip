"""
增强版片段决策提示词
融合技术精度和病毒式传播技巧
"""

from typing import List, Dict, Optional
import json

from app.prompts.base import VisionPrompt
from app.prompts.metadata import PromptMetadata, ModelType, OutputFormat
from app.prompts.registry import PromptRegistry
from app.prompts.viral.techniques import ViralTechniques


@PromptRegistry.register(category="clip_decision", name="enhanced")
class EnhancedClipDecisionPrompt(VisionPrompt):
    """增强版片段决策提示词"""

    def __init__(self):
        metadata = PromptMetadata(
            name="enhanced_clip_decision",
            category="clip_decision",
            version="v2.0",
            model_type=ModelType.VISION,
            output_format=OutputFormat.JSON,
            parameters=[
                "theme",
                "video_analyses",
                "target_duration",
                "viral_style",
                "recommended_hook"
            ],
            description="融合技术精度和病毒式传播技巧的片段决策提示词",
            tags=["clip", "viral", "video_editing", "ai_decision"],
            changelog=[
                "v2.0 - 集成病毒式传播技巧和情感曲线设计",
                "v1.0 - 初始版本，基于技术精度的片段决策"
            ]
        )
        super().__init__(metadata)

    def get_template(self, version: Optional[str] = None) -> str:
        """获取提示词模板"""
        return self._build_enhanced_template()

    def _build_enhanced_template(self) -> str:
        """构建增强版提示词模板"""
        return """你是专业的短视频编辑师，同时精通病毒式传播技巧和技术剪辑。

**任务目标**:
从提供的视频分析中，智能选择最佳片段组合，制作一个{target_duration}秒的短视频，主题为「{theme}」。

**视频分析数据**:
{video_analyses}

**病毒式优化要求**:
风格类型: {viral_style}
推荐钩子: {recommended_hook}

{viral_techniques_guide}

**技术要求**:
1. **时间精度**: 所有时间戳必须精确到小数点后一位（如 00:00:05.5）
2. **音视同步**: 确保片段在音频和视觉上都有意义，避免在句子中间切断
3. **流畅过渡**: 片段之间的连接要自然流畅
4. **内容完整**: 每个片段要有完整的信息点
5. **时长控制**: 总时长误差不超过±3秒

**输出格式** (严格JSON):
{{
  "clips": [
    {{
      "start_time": "00:00:05.0",
      "end_time": "00:00:12.5",
      "duration": 7.5,
      "reason": "开头钩子：使用悬念式引入，前3秒强烈视觉冲击",
      "visual_score": 0.95,
      "audio_score": 0.90,
      "viral_value": 0.92,
      "structure_role": "opening",
      "emotion_target": "好奇/惊讶"
    }},
    {{
      "start_time": "00:00:25.0",
      "end_time": "00:00:38.5",
      "duration": 13.5,
      "reason": "内容展开：痛点共鸣+解决方案预告",
      "visual_score": 0.85,
      "audio_score": 0.88,
      "viral_value": 0.87,
      "structure_role": "development",
      "emotion_target": "共鸣/期待"
    }},
    {{
      "start_time": "00:01:15.5",
      "end_time": "00:01:35.0",
      "duration": 19.5,
      "reason": "高潮时刻：结果展示+惊艳呈现",
      "visual_score": 0.98,
      "audio_score": 0.92,
      "viral_value": 0.95,
      "structure_role": "climax",
      "emotion_target": "惊喜/满足"
    }},
    {{
      "start_time": "00:02:05.0",
      "end_time": "00:02:15.0",
      "duration": 10.0,
      "reason": "收尾升华：总结要点+行动号召",
      "visual_score": 0.88,
      "audio_score": 0.90,
      "viral_value": 0.85,
      "structure_role": "ending",
      "emotion_target": "回味/期待"
    }}
  ],
  "viral_strategy": {{
    "hook_used": "{recommended_hook}",
    "emotion_curve": "快速冲击型",
    "rhythm_pattern": "3秒开场 → 20秒铺垫 → 15秒高潮 → 10秒收尾",
    "transition_style": "快切为主，高潮处适当慢镜头",
    "audio_mixing": "开头音量↑ 吸引注意，高潮处音乐达到峰值",
    "key_moments": ["0-3s钩子", "30-45s高潮", "最后5s行动号召"]
  }},
  "quality_checklist": {{
    "golden_3_seconds": true,
    "emotion_curve_designed": true,
    "rhythm_controlled": true,
    "audio_visual_synced": true,
    "hook_effective": true
  }},
  "total_duration": {target_duration},
  "clip_count": 4,
  "avg_clip_length": 12.5,
  "viral_score": 0.90
}}

**评分标准**:
- viral_value（病毒传播价值）: 35% - 基于钩子效果、情感强度、传播潜力
- content_relevance（内容相关性）: 25% - 与主题契合度
- visual_quality（视觉质量）: 20% - 画面美感、冲击力
- audio_value（音频价值）: 10% - 音效、配音、音乐质量
- rhythm_match（节奏匹配）: 10% - 与病毒式节奏的契合度

**质量检查清单**:
1. ✓ 前3秒是否有明确钩子？
2. ✓ 情感曲线是否清晰（引入→铺垫→高潮→收尾）？
3. ✓ 信息密度是否合理（5-10秒/信息点）？
4. ✓ 音视频是否同步？
5. ✓ 总时长是否符合要求？

请严格按照以上格式输出JSON，确保所有字段完整。"""

    def _get_viral_techniques_guide(self, target_duration: int) -> str:
        """
        获取针对目标时长的病毒式技巧指南

        Args:
            target_duration: 目标时长（秒）

        Returns:
            病毒式技巧指南文本
        """
        # 获取情感曲线
        emotion_curve = ViralTechniques.get_emotion_curve_by_duration(target_duration)

        # 获取节奏指南
        rhythm_guide = ViralTechniques.generate_clip_rhythm_guide(target_duration)

        guide = f"""
**病毒式传播技巧指南**:

1. **黄金三秒法则**:
{ViralTechniques.GOLDEN_3_SECONDS}

2. **推荐情感曲线** ({emotion_curve['name']}):
"""
        for pattern in emotion_curve['pattern']:
            guide += f"\n   - {pattern['time']}: {pattern['emotion']} (强度: {pattern['intensity']})"

        guide += f"\n   提示: {emotion_curve['tips']}"

        guide += f"""

3. **节奏控制建议**:
   - 句子长度: {ViralTechniques.RHYTHM_CONTROL['sentence_length']}
   - 信息密度: {ViralTechniques.RHYTHM_CONTROL['info_density']}
   - 切换频率: {ViralTechniques.RHYTHM_CONTROL['transition_speed']}
   - 情绪曲线: {ViralTechniques.RHYTHM_CONTROL['emotion_curve']}

4. **结构分配** (基于{target_duration}秒):
   - 开头: {rhythm_guide['opening']['start']:.1f}-{rhythm_guide['opening']['end']:.1f}秒 ({rhythm_guide['opening']['focus']})
   - 展开: {rhythm_guide['development']['start']:.1f}-{rhythm_guide['development']['end']:.1f}秒 ({rhythm_guide['development']['focus']})
   - 高潮: {rhythm_guide['climax']['start']:.1f}-{rhythm_guide['climax']['end']:.1f}秒 ({rhythm_guide['climax']['focus']})
   - 收尾: {rhythm_guide['ending']['start']:.1f}-{rhythm_guide['ending']['end']:.1f}秒 ({rhythm_guide['ending']['focus']})
"""
        return guide

    def format_prompt(self, **kwargs) -> str:
        """
        格式化提示词

        Args:
            **kwargs: 包含所有必需参数

        Returns:
            格式化后的提示词
        """
        # 生成病毒式技巧指南
        target_duration = kwargs.get("target_duration", 60)
        viral_guide = self._get_viral_techniques_guide(target_duration)
        kwargs["viral_techniques_guide"] = viral_guide

        # 格式化视频分析数据
        video_analyses = kwargs.get("video_analyses", [])
        if isinstance(video_analyses, list):
            analyses_text = self._format_video_analyses(video_analyses)
            kwargs["video_analyses"] = analyses_text

        # 格式化推荐钩子
        recommended_hook = kwargs.get("recommended_hook", {})
        if isinstance(recommended_hook, dict):
            hook_text = f"{recommended_hook.get('hook_type', '通用')} - {recommended_hook.get('template', '')}"
            kwargs["recommended_hook"] = hook_text

        return super().format_prompt(**kwargs)

    def _format_video_analyses(self, analyses: List[Dict]) -> str:
        """格式化视频分析数据"""
        if not analyses:
            return "暂无视频分析数据"

        formatted = []
        for i, analysis in enumerate(analyses, 1):
            formatted.append(f"""
片段 {i}:
- 时间: {analysis.get('time', 'N/A')}
- 视觉描述: {analysis.get('visual', 'N/A')}
- 音频特征: {analysis.get('audio', 'N/A')}
- 场景评分: {analysis.get('scene_score', 0.0)}
""")

        return "\n".join(formatted)
