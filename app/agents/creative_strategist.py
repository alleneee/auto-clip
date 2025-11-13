"""
CreativeStrategistAgent - 创意策略师

基于视频分析结果，制定创意剪辑策略
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
    ClipStrategyDetail,
    AudioConstraints,
    VideoStyle
)
from app.prompts.viral import ViralHooks, VideoStyle as ViralVideoStyle
from app.config import settings
import structlog

logger = structlog.get_logger(__name__)


class CreativeStrategistAgent:
    """
    创意策略师Agent

    职责：
    - 分析视频内容和风格
    - 推荐病毒式钩子（复用ViralHooks系统）
    - 设计叙事结构
    - 制定开场/主体/结尾的剪辑策略
    """

    def __init__(
        self,
        model: str = "qwen-max",  # 创意任务使用Qwen-max（性价比高）
        api_key: str = None,
        temperature: float = 0.8,  # 创意任务使用较高温度
        provider: Literal["qwen", "deepseek", "dashscope"] = "dashscope"  # 提供商选择
    ):
        """
        初始化创意策略师Agent

        Args:
            model: 模型名称
                - dashscope provider: "qwen-max", "qwen-plus", "qwen-turbo"
                - qwen provider: "qwen-max", "qwen-plus", "qwen-turbo"
                - deepseek provider: "deepseek-chat"
            api_key: API密钥（DashScope或DeepSeek）
            temperature: 温度参数（创意任务建议0.7-0.9）
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

        # 创建Agno Agent
        self.agent = Agent(
            name="CreativeStrategist",
            model=model_instance,
            description="视频剪辑创意策略专家，设计吸引人的叙事结构",
            instructions=[
                "你是资深的短视频创意策略师，精通抖音、YouTube Shorts等平台的爆款逻辑",
                "设计剪辑策略时，必须考虑音视频同步：保持语音完整性，避免切断关键对话",
                "开场3秒是黄金时间：必须用最强的钩子抓住注意力",
                "叙事结构要清晰：问题-方案、总-分-总、悬念-揭秘等经典结构",
                "推荐病毒式钩子时，基于视频实际内容选择最契合的类型",
                "输出必须是严格的JSON格式，符合CreativeStrategy数据模型",
                "所有时长规划必须合理：开场+主体+结尾 = 目标总时长"
            ],
            markdown=False
        )

        logger.info(
            "CreativeStrategistAgent初始化",
            model=model,
            temperature=temperature,
            provider=provider
        )

    def _recommend_viral_hook(self, analysis: MultimodalAnalysis) -> str:
        """
        基于视频分析推荐病毒式钩子

        复用现有的ViralHooks系统
        """
        # 简单的风格映射（基于内容描述）
        # 实际应该用更复杂的逻辑或LLM判断
        timeline_text = " ".join([seg.visual + " " + seg.audio for seg in analysis.timeline[:3]])

        if any(keyword in timeline_text.lower() for keyword in ["教程", "演示", "步骤", "技巧"]):
            style = ViralVideoStyle.TECH
        elif any(keyword in timeline_text.lower() for keyword in ["搞笑", "有趣", "笑"]):
            style = ViralVideoStyle.ENTERTAINMENT
        elif any(keyword in timeline_text.lower() for keyword in ["故事", "经历", "回忆"]):
            style = ViralVideoStyle.STORY
        else:
            style = ViralVideoStyle.TECH  # 默认

        hook = ViralHooks.recommend_hook(style)
        logger.info(f"推荐病毒式钩子", style=style.value, hook_type=hook["hook_type"])
        return hook["hook_type"]

    def _build_strategy_prompt(
        self,
        analyses: List[MultimodalAnalysis],
        config: Dict[str, Any]
    ) -> str:
        """
        构建策略制定提示词

        Args:
            analyses: 所有视频的分析结果
            config: 用户配置（target_duration, platform等）

        Returns:
            完整的策略提示词
        """
        target_duration = config.get("target_duration", 60)
        platform = config.get("platform", "douyin")

        # 汇总视频信息
        videos_summary = []
        for i, analysis in enumerate(analyses, 1):
            summary = f"视频{i}({analysis.video_id}): {analysis.duration:.1f}秒, "
            summary += f"{len(analysis.timeline)}个片段, "
            summary += f"{len(analysis.key_moments)}个关键时刻"
            if analysis.transcription:
                summary += f", 有语音转录"
            videos_summary.append(summary)

        # 提取所有时间轴片段（这是可选择的素材库）
        all_timeline_segments = []
        for analysis in analyses:
            for seg in analysis.timeline:
                all_timeline_segments.append({
                    "video_id": analysis.video_id,
                    "start": seg.start,
                    "end": seg.end,
                    "duration": seg.end - seg.start,
                    "visual": seg.visual[:100],  # 限制长度
                    "audio": seg.audio[:100],
                    "importance": seg.importance
                })

        # 提取关键时刻（用于参考）
        all_key_moments = []
        for analysis in analyses:
            for moment in analysis.key_moments:
                all_key_moments.append({
                    "video_id": analysis.video_id,
                    "timestamp": moment.timestamp,
                    "description": moment.description,
                    "potential": moment.clip_potential
                })

        # 推荐钩子
        recommended_hook = self._recommend_viral_hook(analyses[0]) if analyses else "problem_solution"

        prompt = f"""
基于以下视频分析结果，制定一个创意剪辑策略。

**输入视频**：
{chr(10).join(videos_summary)}

**目标**：
- 平台: {platform}
- 目标时长: {target_duration}秒
- 推荐病毒式钩子: {recommended_hook}

**可选择的时间轴片段（素材库）**：
{json.dumps(all_timeline_segments, ensure_ascii=False, indent=2)}

**关键时刻参考**：
{json.dumps(all_key_moments[:10], ensure_ascii=False, indent=2)}

**策略要求**：

1. **风格定位**（recommended_style）：
   - 从以下选择: tech_tutorial, entertainment, story, news, vlog, product_demo
   - 基于视频实际内容判断

2. **病毒式钩子**（viral_hook）：
   - 推荐: {recommended_hook}
   - 可选其他: problem_solution, shocking_fact, question_hook, before_after, secret_reveal等
   - 必须契合视频内容

3. **叙事结构**（narrative_structure）：
   - 例如: "问题-方案-结果", "总-分-总", "悬念-解释-升华"
   - 清晰的三段式结构

4. **主题**（theme）：
   - 一句话概括视频核心价值
   - 例如: "效率提升技巧", "搞笑日常vlog"

5. **分段策略**（opening/body/ending_strategy）：

   **重要说明**：
   - 你的任务是**从上面提供的时间轴片段中选择精彩片段**，而不是使用完整视频
   - 每个策略应该描述**选择哪些时间轴片段**来组成该部分
   - 选择的片段应该**有足够的时长**（单个片段至少3-8秒）来展现完整内容
   - 各部分选择的片段时长总和应该接近目标时长{target_duration}秒

   **开场策略** (建议占目标时长的10-20%，约{target_duration*0.1:.0f}-{target_duration*0.2:.0f}秒):
   - duration: 建议时长（例如：{target_duration*0.15:.1f}秒）
   - content: 描述从哪些时间轴片段中选择，例如："选择视频1的0-3.5秒片段（高importance评分的开场画面）"
   - reason: 为什么选这些片段作为开场

   **主体策略** (建议占目标时长的60-75%，约{target_duration*0.6:.0f}-{target_duration*0.75:.0f}秒):
   - duration: 建议时长（例如：{target_duration*0.7:.1f}秒）
   - content: 描述选择哪些核心片段，例如："选择视频1的7-11.2秒片段 + 视频2的15-24秒片段，展示核心内容"
   - reason: 为什么选这些片段，如何构成叙事主体

   **结尾策略** (建议占目标时长的10-20%，约{target_duration*0.1:.0f}-{target_duration*0.2:.0f}秒):
   - duration: 建议时长（例如：{target_duration*0.15:.1f}秒）
   - content: 描述结尾片段选择，例如："选择视频2的39-43秒片段作为总结"
   - reason: 为什么选这个片段结尾

   **❌ 错误示例**（选择过短的片段，无法达到目标时长）：
   - 开场：1秒片段
   - 主体：2个1秒片段
   - 结尾：1秒片段
   - 总计：4秒（远低于{target_duration}秒目标）

   **✅ 正确示例**（选择足够长度的有意义片段）：
   - 开场：选择一个3-5秒片段展示吸引力画面
   - 主体：选择2-4个5-10秒片段展示核心内容（总计{target_duration*0.7:.0f}秒左右）
   - 结尾：选择一个3-5秒片段作为总结
   - 总计：约{target_duration}秒

6. **音频约束**（audio_constraints）：
   - keep_speech_complete: true（保持语音完整）
   - avoid_cutting_mid_sentence: true（避免句子中断）
   - preserve_music_rhythm: false（是否保持音乐节奏）

**输出格式**（严格JSON）：
```json
{{
  "recommended_style": "tech_tutorial",
  "viral_hook": "{recommended_hook}",
  "narrative_structure": "问题-方案-结果",
  "theme": "一句话主题",
  "opening_strategy": {{
    "duration": {target_duration*0.15:.1f},
    "content": "选择视频1的0-3.5秒片段（高importance评分的开场画面，包含吸引力元素）",
    "reason": "开场画面吸引力强，适合快速抓住注意力"
  }},
  "body_strategy": {{
    "duration": {target_duration*0.7:.1f},
    "content": "选择视频1的7-11.2秒片段（完整展示核心内容）+ 视频2的15-24秒片段（补充展示）",
    "reason": "这些片段包含核心价值内容，能够完整展示主题"
  }},
  "ending_strategy": {{
    "duration": {target_duration*0.15:.1f},
    "content": "选择视频2的39-43秒片段作为总结画面",
    "reason": "总结画面强化记忆点，适合结尾"
  }},
  "audio_constraints": {{
    "keep_speech_complete": true,
    "avoid_cutting_mid_sentence": true,
    "preserve_music_rhythm": false
  }},
  "target_duration": {target_duration}
}}
```

**重要约束**：
- 总时长 = opening.duration + body.duration + ending.duration ≈ target_duration（允许±10%误差）
- **必须从提供的时间轴片段中选择**，不要凭空创造不存在的时间段
- **选择的片段要有足够长度**（单个片段至少3-8秒），不要选择1-2秒的极短片段
- 必须考虑音视频同步，优先选择包含完整语音或音乐的片段
- 只返回JSON，不要有任何其他文字
"""
        return prompt.strip()

    def generate_strategy(
        self,
        analyses: List[MultimodalAnalysis],
        config: Dict[str, Any]
    ) -> CreativeStrategy:
        """
        生成创意策略

        Args:
            analyses: 所有视频的分析结果
            config: 用户配置

        Returns:
            CreativeStrategy对象
        """
        logger.info(
            "开始制定创意策略",
            videos_count=len(analyses),
            target_duration=config.get("target_duration", 60)
        )

        # 构建提示词
        prompt = self._build_strategy_prompt(analyses, config)

        # 调用Agent
        try:
            response = self.agent.run(prompt)
            content = response.content if hasattr(response, 'content') else str(response)

            logger.info("创意策略师Agent响应", content_preview=content)

            # 解析JSON
            strategy_data = self._parse_json_response(content)

            # 验证并转换为Pydantic模型
            strategy = CreativeStrategy(**strategy_data)

            logger.info(
                "创意策略制定完成",
                style=strategy.recommended_style,
                hook=strategy.viral_hook,
                structure=strategy.narrative_structure
            )

            return strategy

        except Exception as e:
            logger.error(
                "创意策略制定失败",
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """解析JSON响应（同ContentAnalyzerAgent）"""
        content = content.strip()

        # 提取JSON
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
def create_creative_strategist(
    model: str = "gpt-4o",
    **kwargs
) -> CreativeStrategistAgent:
    """创建CreativeStrategistAgent实例"""
    return CreativeStrategistAgent(model=model, **kwargs)
