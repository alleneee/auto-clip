"""
TechnicalPlannerAgent - 技术规划师

将创意策略转化为可执行的技术剪辑方案
"""

import json
from typing import Dict, Any, List, Literal, Optional
from agno.agent import Agent
from agno.models.deepseek import DeepSeek
from agno.models.dashscope import DashScope
from agno.models.openai import OpenAIChat

from app.models.agno_models import (
    MultimodalAnalysis,
    CreativeStrategy,
    TechnicalPlan,
    ClipSegment,
    TransitionConfig,
    AudioHandling,
    FeasibilityCheck,
    SegmentRole
)
from app.config import settings
import structlog

logger = structlog.get_logger(__name__)


class TechnicalPlannerAgent:
    """
    技术规划师Agent

    职责：
    - 将创意策略转化为精确的剪辑指令
    - 选择具体的时间段和片段
    - 规划转场效果
    - 检查技术可行性
    """

    def __init__(
        self,
        model: str = "qwen-max",
        api_key: str = None,
        temperature: float = 0.4,  # 技术任务使用中等温度
        provider: Literal["qwen", "deepseek", "dashscope"] = "dashscope"
    ):
        """
        初始化技术规划师Agent

        Args:
            model: 模型名称
                - dashscope provider: "qwen-max", "qwen-plus", "qwen-turbo"
                - qwen provider: "qwen-max", "qwen-plus", "qwen-turbo"
                - deepseek provider: "deepseek-chat"
            api_key: API密钥（DashScope或DeepSeek）
            temperature: 温度参数
            provider: 提供商（"dashscope", "qwen" 或 "deepseek"）
        """
        self.model_name = model
        self.provider = provider

        # 根据provider选择正确的模型类
        if provider in ["qwen", "dashscope"]:
            model_instance = DashScope(
                id=model,
                api_key=api_key or settings.DASHSCOPE_API_KEY,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                temperature=temperature
            )
        elif provider == "deepseek":
            model_instance = DeepSeek(
                id=model,
                api_key=api_key,
                temperature=temperature
            )
        else:
            raise ValueError(f"不支持的provider: {provider}")

        self.agent = Agent(
            name="TechnicalPlanner",
            model=model_instance,
            description="视频剪辑技术方案规划专家，生成可执行的剪辑指令",
            instructions=[
                "你是专业的视频剪辑技术专家，精通MoviePy和视频编辑流程",
                "根据创意策略，选择最合适的视频片段和时间点",
                "确保所有时间戳精确，符合视频实际时长",
                "转场设计要自然：淡入淡出0.5秒，避免生硬切换",
                "音频处理要专业：保持语音完整，音乐在片段间淡出",
                "输出必须是严格的JSON格式，符合TechnicalPlan数据模型",
                "每个片段必须包含：video_id, start_time, end_time, role, transitions, reason",
                "进行可行性检查：时长匹配度、音频连续性、技术问题"
            ],
            markdown=False
        )

        logger.info(
            "TechnicalPlannerAgent初始化",
            model=model,
            provider=provider
        )

    def _build_plan_prompt(
        self,
        analyses: List[MultimodalAnalysis],
        strategy: CreativeStrategy,
        config: Dict[str, Any],
        previous_review: Optional[Any] = None
    ) -> str:
        """构建技术规划提示词（支持评审反馈）"""

        # 汇总视频数据
        videos_data = []
        for analysis in analyses:
            video_info = {
                "video_id": analysis.video_id,
                "duration": analysis.duration,
                "key_moments": [
                    {
                        "timestamp": m.timestamp,
                        "description": m.description,
                        "potential": m.clip_potential
                    }
                    for m in analysis.key_moments
                ],
                "has_speech": bool(analysis.transcription),
                "speech_segments": analysis.audio_layers.speech_segments if analysis.transcription else []
            }
            videos_data.append(video_info)

        prompt = f"""
基于以下创意策略和视频分析，生成详细的技术剪辑方案。

**创意策略**：
- 风格: {strategy.recommended_style}
- 钩子: {strategy.viral_hook}
- 结构: {strategy.narrative_structure}
- 主题: {strategy.theme}

**分段要求**：
- 开场: {strategy.opening_strategy.duration}秒 - {strategy.opening_strategy.content}
- 主体: {strategy.body_strategy.duration}秒 - {strategy.body_strategy.content}
- 结尾: {strategy.ending_strategy.duration}秒 - {strategy.ending_strategy.content}
- 目标总时长: {strategy.target_duration}秒

**可用视频数据**：
{json.dumps(videos_data, ensure_ascii=False, indent=2)}

**技术要求**：

1. **片段选择**（segments）：
   每个片段包含：
   - video_id: 源视频ID
   - start_time: 开始时间（秒，精确到0.1）
   - end_time: 结束时间（秒）
   - duration: 片段时长（自动计算：end - start）
   - role: opening/body/ending/transition
   - audio_intact: 音频是否完整保留（语音片段必须true）
   - transitions: {{transition_in: "fade/cut/none", transition_out: "fade/cut/none", fade_duration: 0.5}}
   - reason: 选择此片段的技术理由
   - speech_content: （可选）包含的语音内容

2. **时间轴规划**：
   - 按照opening → body → ending顺序排列
   - 避免切断语音：如果有speech_segments，片段边界应对齐语音边界
   - 转场重叠：fade转场会有0.5秒重叠，计算总时长时要考虑

3. **音频处理**（audio_handling）：
   - preserve_speech: true（保留语音）
   - background_music: "fade_between_segments"（片段间淡出）
   - volume_normalization: true（音量归一化）

4. **可行性检查**（feasibility）：
   - duration_match: 实际总时长与目标时长的匹配度（0-1）
   - audio_continuity: "excellent/good/fair/poor"（音频连续性评估）
   - technical_issues: []（技术问题列表，如时间超限、片段冲突等）

**输出格式**（严格JSON）：
```json
{{
  "segments": [
    {{
      "video_id": "视频ID",
      "start_time": 15.0,
      "end_time": 18.0,
      "duration": 3.0,
      "role": "opening",
      "audio_intact": true,
      "transitions": {{
        "transition_in": "none",
        "transition_out": "fade",
        "fade_duration": 0.5
      }},
      "reason": "音视频同步的强调点，clip_potential=0.95",
      "speech_content": "这个方法可以节省50%时间"
    }},
    ...
  ],
  "total_duration": 58.0,
  "audio_handling": {{
    "preserve_speech": true,
    "background_music": "fade_between_segments",
    "volume_normalization": true
  }},
  "feasibility": {{
    "duration_match": 0.97,
    "audio_continuity": "good",
    "technical_issues": []
  }}
}}
```

**重要约束**：
1. 所有时间戳必须在视频实际时长范围内
2. **total_duration必须等于所有segments的duration之和**（允许0.5秒误差）
   - ❌ 错误示例：segments总和10.2秒，但total_duration写成20.0（目标时长）
   - ✅ 正确示例：segments总和10.2秒，total_duration也写10.2
   - 注意：total_duration是"实际剪辑后的总时长"，不是"目标时长"
3. 计算total_duration时考虑转场重叠（每个fade转场减0.5秒）
4. 语音片段的audio_intact必须为true
5. 只返回JSON，不要有任何其他文字
"""

        # 如果有前一次评审反馈，添加改进要求
        if previous_review:
            feedback_section = f"""

**⚠️ 前一次方案的评审反馈（需要改进）**：

**评分**: {previous_review.overall_score:.1f}/10.0 (未通过)

**质量维度评分**:
- 叙事连贯性: {previous_review.quality_dimensions.narrative_coherence:.1f}
- 音画同步: {previous_review.quality_dimensions.audio_video_sync:.1f}
- 内容覆盖: {previous_review.quality_dimensions.content_coverage:.1f}
- 制作质量: {previous_review.quality_dimensions.production_quality:.1f}
- 吸引力: {previous_review.quality_dimensions.engagement_potential:.1f}

**需要改进的问题**:
{chr(10).join(f"- {improvement}" for improvement in previous_review.feedback.improvements)}

**具体修订建议**:
{chr(10).join(f"- {suggestion}" for suggestion in previous_review.revision_suggestions) if previous_review.revision_suggestions else "无具体建议"}

**本次方案必须解决以上问题，并提升质量评分至 ≥7.0 分！**
"""
            prompt += feedback_section

        return prompt.strip()

    def create_plan(
        self,
        analyses: List[MultimodalAnalysis],
        strategy: CreativeStrategy,
        config: Dict[str, Any],
        previous_review: Optional[Any] = None  # QualityReview对象
    ) -> TechnicalPlan:
        """
        创建技术剪辑方案（支持基于评审反馈迭代改进）

        Args:
            analyses: 所有视频的分析结果
            strategy: 创意策略
            config: 用户配置
            previous_review: 前一次质量评审结果（可选）
                - 如果提供，会在提示词中包含改进建议

        Returns:
            TechnicalPlan对象
        """
        if previous_review:
            logger.info(
                "基于评审反馈重新制定技术方案",
                videos_count=len(analyses),
                previous_score=previous_review.overall_score,
                improvements_needed=len(previous_review.feedback.improvements)
            )
        else:
            logger.info(
                "开始制定技术方案",
                videos_count=len(analyses),
                strategy_style=strategy.recommended_style
            )

        # 构建提示词（包含评审反馈）
        prompt = self._build_plan_prompt(analyses, strategy, config, previous_review)

        # 调用Agent
        try:
            response = self.agent.run(prompt)
            content = response.content if hasattr(response, 'content') else str(response)

            logger.info("视频剪辑技术方案规划专家响应", content_preview=content)

            # 解析JSON
            plan_data = self._parse_json_response(content)

            # 修正segment时间戳（过滤无效segment，重新计算duration）
            plan_data = self._fix_segment_times(plan_data)

            # 自动修正total_duration为片段总和
            plan_data = self._fix_total_duration(plan_data)

            # 验证并转换为Pydantic模型
            plan = TechnicalPlan(**plan_data)

            logger.info(
                "技术方案制定完成",
                segments_count=len(plan.segments),
                total_duration=plan.total_duration,
                duration_match=plan.feasibility.duration_match
            )

            return plan

        except Exception as e:
            logger.error(
                "技术方案制定失败",
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    def _fix_segment_times(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        修正和验证segment时间戳

        1. 过滤掉end_time <= start_time的无效segment
        2. 重新计算duration确保正确
        3. 确保时间戳精度一致（保留1位小数）
        """
        if "segments" not in data or not isinstance(data["segments"], list):
            return data

        original_count = len(data["segments"])
        valid_segments = []

        for i, seg in enumerate(data["segments"]):
            start_time = seg.get("start_time")
            end_time = seg.get("end_time")

            # 检查时间戳是否存在
            if start_time is None or end_time is None:
                logger.warning(
                    f"片段{i}缺少时间戳，跳过",
                    segment=seg
                )
                continue

            # 确保时间戳精度（保留1位小数）
            start_time = round(float(start_time), 1)
            end_time = round(float(end_time), 1)

            # 检查时间戳有效性
            if end_time <= start_time:
                logger.warning(
                    f"片段{i}时间戳无效（end_time <= start_time），过滤",
                    start_time=start_time,
                    end_time=end_time,
                    video_id=seg.get("video_id"),
                    role=seg.get("role")
                )
                continue

            # 重新计算duration
            duration = round(end_time - start_time, 1)

            # 更新segment数据
            seg["start_time"] = start_time
            seg["end_time"] = end_time
            seg["duration"] = duration

            valid_segments.append(seg)

        # 更新segments列表
        data["segments"] = valid_segments

        if len(valid_segments) < original_count:
            logger.warning(
                "过滤了无效的segment",
                original_count=original_count,
                valid_count=len(valid_segments),
                filtered_count=original_count - len(valid_segments)
            )

        return data

    def _fix_total_duration(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        自动修正total_duration为片段总和

        AI模型经常将target_duration误当作total_duration，
        实际上total_duration必须等于所有segments的duration之和
        """
        if "segments" in data and isinstance(data["segments"], list):
            # 计算实际的片段总和
            calculated_total = sum(seg.get("duration", 0) for seg in data["segments"])

            if "total_duration" in data:
                original_total = data["total_duration"]
                # 如果差异超过0.5秒，自动修正
                if abs(calculated_total - original_total) > 0.5:
                    logger.warning(
                        "自动修正total_duration",
                        original=original_total,
                        calculated=calculated_total,
                        segments_count=len(data["segments"])
                    )
                    data["total_duration"] = round(calculated_total, 1)
            else:
                # 如果缺少total_duration，自动添加
                data["total_duration"] = round(calculated_total, 1)
                logger.info(
                    "自动添加total_duration",
                    total=data["total_duration"],
                    segments_count=len(data["segments"])
                )

        return data

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """解析JSON响应"""
        content = content.strip()

        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            content = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            content = content[start:end].strip()

        try:
            data = json.loads(content)
            return data
        except json.JSONDecodeError as e:
            logger.error("JSON解析失败", error=str(e))
            content = content.replace("'", '"')
            content = content.rstrip(',')
            try:
                data = json.loads(content)
                logger.info("JSON修复成功")
                return data
            except:
                raise ValueError(f"无法解析JSON响应: {e}")


# 便捷函数
def create_technical_planner(
    model: str = "gpt-4o",
    **kwargs
) -> TechnicalPlannerAgent:
    """创建TechnicalPlannerAgent实例"""
    return TechnicalPlannerAgent(model=model, **kwargs)
