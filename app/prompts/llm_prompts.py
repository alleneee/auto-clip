"""
LLM提示词管理模块
集中管理所有大模型调用的提示词
"""
from typing import Dict, Any, List


class VideoAnalysisPrompts:
    """视频分析相关提示词"""

    # 视觉内容分析默认提示词
    VISUAL_ANALYSIS_DEFAULT = """请详细分析这个视频的内容：
1. 主要场景和内容描述
2. 关键人物和动作
3. 情感色彩和氛围
4. 精彩或重要的时刻
5. 整体风格和主题"""

    # 视觉内容深度分析提示词
    VISUAL_ANALYSIS_DETAILED = """作为专业的视频内容分析师，请从以下维度深入分析这个视频：

【场景分析】
- 主要场景和环境特征
- 场景切换频率和节奏
- 视觉构图和色彩运用

【内容要素】
- 关键人物及其行为动作
- 物体和道具的重要性
- 文字信息（字幕、标识等）

【情感与氛围】
- 整体情感基调
- 情绪变化曲线
- 氛围营造手法

【精彩时刻】
- 高潮片段和关键转折点
- 视觉冲击力强的镜头
- 值得保留的精华部分

【风格与主题】
- 视频风格定位
- 核心主题和立意
- 目标受众画像"""

    # 快速概览提示词（用于批量处理）
    VISUAL_ANALYSIS_QUICK = """用3-5句话快速概括这个视频的核心内容：
- 主要内容是什么？
- 有哪些亮点？
- 整体风格如何？"""


class ThemeGenerationPrompts:
    """主题生成相关提示词"""

    @staticmethod
    def generate_theme_prompt(analyses: List[Dict[str, Any]]) -> str:
        """
        生成主题提示词

        Args:
            analyses: 视频分析结果列表

        Returns:
            完整的主题生成提示词
        """
        # 构建分析文本
        analysis_text = "\n\n".join(
            [
                f"【视频{i+1}】\n"
                f"视觉内容: {a.get('visual_analysis', '无')}\n"
                f"语音内容: {a.get('transcript', '无')}"
                for i, a in enumerate(analyses)
            ]
        )

        return f"""基于以下多个视频的分析结果，生成一个简洁有力的主题标题（10-20字）：

{analysis_text}

【要求】
1. 主题要准确概括所有视频的核心内容
2. 具有吸引力和感染力
3. 简洁明了，易于理解
4. 只输出主题标题，不需要额外解释"""

    # 系统角色提示词
    THEME_GENERATION_SYSTEM = """你是一位专业的视频内容策划专家，擅长从多个视频素材中提炼核心主题。
你的目标是创造简洁、有力、吸引人的主题标题。"""


class ClipDecisionPrompts:
    """剪辑决策相关提示词（LLM Pass 2）"""

    @staticmethod
    def generate_clip_decision_prompt(
        theme: str, analyses: List[Dict[str, Any]], target_duration: int = 60
    ) -> str:
        """
        生成剪辑决策提示词

        Args:
            theme: 主题标题
            analyses: 视频分析结果列表
            target_duration: 目标时长（秒）

        Returns:
            完整的剪辑决策提示词
        """
        # 构建视频信息
        video_info = "\n\n".join(
            [
                f"【视频{i+1}】(ID: {a.get('video_id', 'unknown')})\n"
                f"时长: {a.get('duration', 0):.1f}秒\n"
                f"视觉分析: {a.get('visual_analysis', '')}\n"
                f"语音内容: {a.get('transcript', '')}"
                for i, a in enumerate(analyses)
            ]
        )

        return f"""你是一位专业的视频剪辑师。现在需要基于主题"{theme}"从多个视频中选择精彩片段进行剪辑。

【视频素材】
{video_info}

【剪辑要求】
1. 目标时长: {target_duration}秒（允许±10%误差）
2. 剪辑片段数量: 3-8个
3. 每个片段时长: 5-20秒
4. 片段之间要有逻辑连贯性和节奏感

【输出格式】（JSON）
请严格按照以下JSON格式输出剪辑决策：

{{
  "theme": "{theme}",
  "clips": [
    {{
      "video_id": "视频ID",
      "start_time": 起始时间（秒）,
      "end_time": 结束时间（秒）,
      "reason": "选择这个片段的原因",
      "confidence": 0.95,
      "tags": ["标签1", "标签2"]
    }}
  ]
}}

【评分标准】
- 内容相关性: 与主题的契合度
- 视觉质量: 画面精彩程度
- 情感共鸣: 能否引发观众情感反应
- 节奏把控: 片段组合的流畅度

请开始分析并输出剪辑决策："""

    # 系统角色提示词
    CLIP_DECISION_SYSTEM = """你是一位经验丰富的视频剪辑师和内容策划师。
你精通视频叙事、节奏把控和情感传递。
你的任务是从原始素材中挑选最精彩的片段，组合成吸引人的短视频。
请务必输出有效的JSON格式数据。"""


class PromptTemplates:
    """通用提示词模板"""

    @staticmethod
    def wrap_with_format_instruction(content: str, format_type: str = "json") -> str:
        """
        为提示词添加格式化指令

        Args:
            content: 原始内容
            format_type: 格式类型（json/markdown/text）

        Returns:
            包装后的提示词
        """
        format_instructions = {
            "json": "请严格按照JSON格式输出，确保数据可以被解析。",
            "markdown": "请使用Markdown格式输出，包含适当的标题和列表。",
            "text": "请使用纯文本格式输出，简洁明了。",
        }

        instruction = format_instructions.get(format_type, "")
        return f"{content}\n\n【输出格式要求】\n{instruction}"

    @staticmethod
    def add_context(base_prompt: str, context: Dict[str, Any]) -> str:
        """
        为提示词添加上下文信息

        Args:
            base_prompt: 基础提示词
            context: 上下文信息

        Returns:
            包含上下文的提示词
        """
        context_text = "\n".join(
            [f"{key}: {value}" for key, value in context.items()]
        )
        return f"【上下文信息】\n{context_text}\n\n{base_prompt}"


class AudioTranscriptPrompts:
    """语音转写分析相关提示词"""

    # 语音内容总结
    TRANSCRIPT_SUMMARY = """请基于以下语音转写内容，提炼核心要点：

{transcript}

请从以下角度进行总结：
1. 主要话题和讨论内容
2. 关键信息和重点
3. 情感基调和氛围
4. 值得关注的金句或亮点"""

    # 语音与视觉内容融合分析
    AUDIO_VISUAL_FUSION = """请综合分析视频的视觉内容和语音内容：

【视觉内容】
{visual_analysis}

【语音内容】
{transcript}

请分析：
1. 视觉与语音内容的一致性和关联性
2. 哪些时间段的音视频配合最精彩
3. 内容主题和核心价值
4. 建议保留的精华片段及理由"""


# 导出所有提示词类
__all__ = [
    "VideoAnalysisPrompts",
    "ThemeGenerationPrompts",
    "ClipDecisionPrompts",
    "PromptTemplates",
    "AudioTranscriptPrompts",
]
