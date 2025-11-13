"""
QualityReviewerAgent - 质量评审员

评估剪辑方案的质量，给出改进建议
"""

import json
from typing import Dict, Any, List, Literal
from agno.agent import Agent
from agno.models.deepseek import DeepSeek
from agno.models.dashscope import DashScope
from agno.models.openai import OpenAIChat

from app.models.agno_models import (
    MultimodalAnalysis,
    CreativeStrategy,
    TechnicalPlan,
    QualityReview,
    QualityDimensions,
    ReviewFeedback
)
from app.config import settings
import structlog

logger = structlog.get_logger(__name__)


class QualityReviewerAgent:
    """
    质量评审员Agent

    职责：
    - 评估剪辑方案质量（5维度评分）
    - 检查叙事连贯性、音画同步、内容覆盖等
    - 给出改进建议
    - 决定是否通过评审
    """

    def __init__(
        self,
        model: str = "qwen-max",
        api_key: str = None,
        temperature: float = 0.3,  # 评审任务使用低温度
        pass_threshold: float = 7.0,  # 总分阈值
        provider: Literal["qwen", "deepseek", "dashscope"] = "dashscope"
    ):
        """
        初始化质量评审员Agent

        Args:
            model: 模型名称
                - dashscope provider: "qwen-max", "qwen-plus", "qwen-turbo"
                - qwen provider: "qwen-max", "qwen-plus", "qwen-turbo"
                - deepseek provider: "deepseek-chat"
            api_key: API密钥（DashScope或DeepSeek）
            temperature: 温度参数
            pass_threshold: 通过阈值（总分>=此值视为通过）
            provider: 提供商（"dashscope", "qwen" 或 "deepseek"）
        """
        self.model_name = model
        self.pass_threshold = pass_threshold
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
            name="QualityReviewer",
            model=model_instance,
            description="视频剪辑质量评审专家，严格把控方案质量",
            instructions=[
                "你是资深的视频质量评审专家，对剪辑方案进行严格评估",
                "评分标准要客观：基于实际数据，不要过分乐观或悲观",
                "5维度评分系统（每项0-10分）：",
                "1. 叙事连贯性(narrative_coherence)：故事是否流畅、逻辑清晰",
                "2. 音画同步(audio_video_sync)：音频与视觉是否配合良好",
                "3. 内容覆盖(content_coverage)：是否充分利用了关键内容",
                "4. 制作质量(production_quality)：技术方案是否专业",
                "5. 吸引力(engagement_potential)：是否能吸引观众",
                "总分 = 5维度平均分",
                "通过标准：总分>=7.0且无重大技术问题",
                "输出必须是严格的JSON格式，符合QualityReview数据模型"
            ],
            markdown=False
        )

        logger.info(
            "QualityReviewerAgent初始化",
            model=model,
            pass_threshold=pass_threshold,
            provider=provider
        )

    def _build_review_prompt(
        self,
        analyses: List[MultimodalAnalysis],
        strategy: CreativeStrategy,
        plan: TechnicalPlan
    ) -> str:
        """构建评审提示词"""

        # 汇总方案信息
        plan_summary = {
            "segments_count": len(plan.segments),
            "total_duration": plan.total_duration,
            "target_duration": strategy.target_duration,
            "duration_match": plan.feasibility.duration_match,
            "audio_continuity": plan.feasibility.audio_continuity,
            "technical_issues": plan.feasibility.technical_issues,
            "segments": [
                {
                    "role": seg.role,
                    "duration": seg.duration,
                    "audio_intact": seg.audio_intact,
                    "reason": seg.reason
                }
                for seg in plan.segments
            ]
        }

        prompt = f"""
对以下剪辑方案进行全面的质量评审。

**创意策略**：
- 风格: {strategy.recommended_style}
- 钩子: {strategy.viral_hook}
- 结构: {strategy.narrative_structure}
- 主题: {strategy.theme}
- 目标时长: {strategy.target_duration}秒

**技术方案摘要**：
{json.dumps(plan_summary, ensure_ascii=False, indent=2)}

**评审标准**（0-10分制）：

1. **叙事连贯性** (narrative_coherence)：
   - 开场-主体-结尾逻辑是否流畅
   - 是否符合声称的叙事结构（{strategy.narrative_structure}）
   - 片段衔接是否自然
   评分要点：逻辑清晰=8-10分，基本连贯=6-7分，有跳跃=4-5分，混乱=0-3分

2. **音画同步** (audio_video_sync)：
   - 语音片段是否完整保留（audio_intact=true）
   - 转场设计是否合理
   - 音频处理方案是否专业
   评分要点：完美同步=8-10分，良好=6-7分，一般=4-5分，有问题=0-3分

3. **内容覆盖** (content_coverage)：
   - 是否利用了高潜力关键时刻（clip_potential高的）
   - 核心内容是否覆盖充分
   - 是否有浪费的高质量素材
   评分要点：充分利用=8-10分，基本覆盖=6-7分，不足=4-5分，遗漏重要内容=0-3分

4. **制作质量** (production_quality)：
   - 时间戳是否精确
   - 转场效果是否专业
   - 技术可行性检查是否通过
   评分要点：专业水准=8-10分，合格=6-7分，有瑕疵=4-5分，技术问题=0-3分

5. **吸引力** (engagement_potential)：
   - 开场3秒是否足够抓人
   - 病毒式钩子应用是否恰当
   - 整体节奏是否符合平台特点
   评分要点：极具吸引力=8-10分，有吸引力=6-7分，一般=4-5分，无吸引力=0-3分

**评审结果要求**：

1. **总分计算**：5维度平均分
2. **通过判定**：总分>={self.pass_threshold} 且 technical_issues为空
3. **优点总结**（strengths）：列出2-3个亮点
4. **改进建议**（improvements）：列出1-3个可优化点
5. **修订建议**（revision_suggestions）：如果不通过，给出具体修改建议

**输出格式**（严格JSON）：
```json
{{
  "overall_score": 8.2,
  "quality_dimensions": {{
    "narrative_coherence": 8.5,
    "audio_video_sync": 8.0,
    "content_coverage": 8.0,
    "production_quality": 8.5,
    "engagement_potential": 8.0
  }},
  "pass_review": true,
  "feedback": {{
    "strengths": [
      "开场选用了clip_potential=0.95的强势片段",
      "音视频同步质量高，语音完整保留",
      "叙事结构清晰，符合'问题-方案-结果'框架"
    ],
    "improvements": [
      "主体部分可以再紧凑2秒",
      "结尾转场可以更流畅"
    ]
  }},
  "revision_suggestions": []
}}
```

**评分原则**：
- 客观公正，基于实际数据
- 不要过分宽容或严苛
- 5维度评分应有差异，不要都是同一分数
- 总分必须是5维度的精确平均值（误差<0.1）
- 只返回JSON，不要有任何其他文字
"""
        return prompt.strip()

    def review(
        self,
        analyses: List[MultimodalAnalysis],
        strategy: CreativeStrategy,
        plan: TechnicalPlan
    ) -> QualityReview:
        """
        评审剪辑方案

        Args:
            analyses: 所有视频的分析结果
            strategy: 创意策略
            plan: 技术方案

        Returns:
            QualityReview对象
        """
        logger.info(
            "开始质量评审",
            plan_segments=len(plan.segments),
            plan_duration=plan.total_duration
        )

        # 构建提示词
        prompt = self._build_review_prompt(analyses, strategy, plan)

        # 调用Agent
        try:
            response = self.agent.run(prompt)
            content = response.content if hasattr(response, 'content') else str(response)

            logger.info("视频剪辑质量评审agent响应", content_preview=content)

            # 解析JSON
            review_data = self._parse_json_response(content)

            # 验证并转换为Pydantic模型
            review = QualityReview(**review_data)

            logger.info(
                "质量评审完成",
                overall_score=review.overall_score,
                pass_review=review.pass_review,
                strengths_count=len(review.feedback.strengths),
                improvements_count=len(review.feedback.improvements)
            )

            return review

        except Exception as e:
            logger.error(
                "质量评审失败",
                error=str(e),
                error_type=type(e).__name__
            )
            raise

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
def create_quality_reviewer(
    model: str = "gpt-4o",
    **kwargs
) -> QualityReviewerAgent:
    """创建QualityReviewerAgent实例"""
    return QualityReviewerAgent(model=model, **kwargs)
