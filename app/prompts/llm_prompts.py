"""
LLM提示词管理模块
集中管理所有大模型调用的提示词
"""
from typing import Dict, Any, List


class VideoAnalysisPrompts:
    """视频分析相关提示词"""

    # JSON格式视频分段分析（推荐使用）
    VISUAL_ANALYSIS_JSON = """请作为专业的视频内容分析师，对这个视频进行分段分析并输出JSON格式。

【分析要求】
1. 将视频划分为多个有意义的时间段（建议3-8个）
2. 每个时间段应该是一个完整的场景或主题
3. 识别每个时间段的内容特征和精彩点
4. 评估每个时间段的重要性和价值

【输出格式】（严格遵循JSON格式，不要添加markdown代码块标记）
{{
  "video_summary": "视频整体概述（1-2句话）",
  "total_duration": 视频总时长（秒，浮点数）,
  "style": "视频风格（如：商业广告、生活记录、教学演示等）",
  "segments": [
    {{
      "segment_id": 1,
      "start_time": 起始时间（秒，浮点数）,
      "end_time": 结束时间（秒，浮点数）,
      "duration": 时长（秒，浮点数）,
      "content": "该时间段的核心内容描述",
      "scene_description": "场景和画面特征",
      "actions": "人物动作、镜头运动等",
      "highlights": [
        "精彩点1：具体描述",
        "精彩点2：具体描述"
      ],
      "emotion": "情感基调（如：欢快、平静、紧张等）",
      "importance_score": 0.85
    }}
  ],
  "overall_highlights": [
    "整体最精彩的亮点1",
    "整体最精彩的亮点2"
  ],
  "recommended_clips": [
    {{
      "start_time": 推荐片段起始时间（秒），
      "end_time": 推荐片段结束时间（秒），
      "reason": "推荐理由（为什么这段值得保留）"
    }}
  ]
}}

【评分说明】
- importance_score: 该时间段的重要性评分（0.0-1.0之间，1.0为最重要）
- 评分考虑因素：视觉冲击力、内容价值、情感共鸣、独特性

【注意事项】
1. 时间段不能重叠，按时间顺序排列
2. 所有时间使用秒为单位，保留1位小数
3. 确保JSON格式完全正确，可被直接解析
4. highlights数组至少包含1-3个精彩点
5. recommended_clips建议1-5个最值得保留的片段

请严格按照上述JSON格式输出分析结果，不要添加任何额外的文字说明。"""

    # 简化版JSON分析（快速处理）
    VISUAL_ANALYSIS_JSON_SIMPLE = """请对视频进行快速分段分析，输出JSON格式。

输出格式（不要添加markdown代码块标记）：
{{
  "video_summary": "简要概述",
  "segments": [
    {{
      "start_time": 起始时间（秒）,
      "end_time": 结束时间（秒）,
      "content": "内容描述",
      "highlights": ["精彩点1", "精彩点2"],
      "importance_score": 0.8
    }}
  ],
  "recommended_clips": [
    {{
      "start_time": 时间,
      "end_time": 时间,
      "reason": "理由"
    }}
  ]
}}

要求：
1. 划分3-5个时间段
2. 每段包含主要内容和精彩点
3. 严格JSON格式，可直接解析
4. 推荐1-3个最佳片段"""




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
        生成剪辑决策提示词（兼容旧版简单文本格式）

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

    @staticmethod
    def generate_enhanced_clip_decision_prompt(
        theme: str,
        video_analyses: List[Dict[str, Any]],
        target_duration: int = 60
    ) -> str:
        """
        生成增强版剪辑决策提示词（整合视觉JSON和句级ASR）

        Args:
            theme: 主题标题
            video_analyses: 视频分析结果列表，每个包含:
                - video_id: 视频ID
                - duration: 时长（秒）
                - visual_analysis_json: VL模型JSON分析结果（包含segments、highlights等）
                - asr_transcription: ASR识别结果（包含sentences列表，含begin_time、end_time）
            target_duration: 目标时长（秒）

        Returns:
            完整的增强版剪辑决策提示词
        """
        # 构建每个视频的详细分析信息
        video_sections = []

        for i, analysis in enumerate(video_analyses):
            video_id = analysis.get('video_id', f'video_{i+1}')
            duration = analysis.get('duration', 0)

            # 1. 视觉分析JSON（包含时间分段、精彩点、重要性评分）
            visual_json = analysis.get('visual_analysis_json', {})

            # 2. ASR转写结果（句级时间戳）
            asr_data = analysis.get('asr_transcription', {})
            sentences = asr_data.get('sentences', [])

            # 构建视频分析文本
            section = f"""【视频{i+1}】(ID: {video_id}, 时长: {duration:.1f}秒)

▸ 视觉分析摘要:
  风格: {visual_json.get('style', '未知')}
  概述: {visual_json.get('video_summary', '无')}

▸ 视觉时间分段（共{len(visual_json.get('segments', []))}段）:"""

            # 添加每个视觉分段的详细信息
            for seg in visual_json.get('segments', []):
                section += f"""
  [{seg.get('start_time', 0):.1f}s - {seg.get('end_time', 0):.1f}s] (重要性: {seg.get('importance_score', 0):.2f})
    内容: {seg.get('content', '')}
    场景: {seg.get('scene_description', '')}
    动作: {seg.get('actions', '')}
    情感: {seg.get('emotion', '')}
    精彩点: {', '.join(seg.get('highlights', []))}"""

            # 添加整体精彩亮点
            overall_highlights = visual_json.get('overall_highlights', [])
            if overall_highlights:
                section += f"\n  \n▸ 整体精彩亮点:\n"
                for highlight in overall_highlights:
                    section += f"  • {highlight}\n"

            # 添加推荐片段
            recommended_clips = visual_json.get('recommended_clips', [])
            if recommended_clips:
                section += f"\n▸ VL模型推荐片段:\n"
                for clip in recommended_clips:
                    section += f"  • [{clip.get('start_time', 0):.1f}s - {clip.get('end_time', 0):.1f}s] {clip.get('reason', '')}\n"

            # 添加ASR句级转写（带时间戳）
            if sentences:
                section += f"\n▸ 语音内容（句级时间戳，共{len(sentences)}句）:\n"
                for sent in sentences:
                    begin_time = sent.get('begin_time', 0) / 1000.0  # 毫秒转秒
                    end_time = sent.get('end_time', 0) / 1000.0
                    text = sent.get('text', '')
                    speaker_id = sent.get('speaker_id')

                    if speaker_id is not None:
                        section += f"  [{begin_time:.2f}s - {end_time:.2f}s] [说话人{speaker_id}] {text}\n"
                    else:
                        section += f"  [{begin_time:.2f}s - {end_time:.2f}s] {text}\n"
            else:
                # 如果没有句级数据，使用完整文本
                full_text = asr_data.get('text', '')
                if full_text:
                    section += f"\n▸ 语音内容: {full_text}\n"

            video_sections.append(section)

        # 组合所有视频的分析
        all_videos_info = "\n\n".join(video_sections)

        # 生成完整提示词
        return f"""你是一位专业的视频剪辑师和内容策划师。现在需要基于主题"{theme}"从多个视频中选择最精彩的片段进行混剪。

【视频素材分析】
{all_videos_info}

【剪辑决策要求】
1. 目标时长: {target_duration}秒（允许±10%误差，即{target_duration * 0.9:.0f}-{target_duration * 1.1:.0f}秒）
2. 剪辑片段数量: 3-8个片段
3. 每个片段时长: 5-20秒
4. 片段选择策略:
   - 优先选择高重要性评分（importance_score > 0.7）的视觉分段
   - 考虑VL模型推荐的精彩片段
   - 关注音视频内容的协同性（语音与画面的配合）
   - 保持片段之间的逻辑连贯性和节奏感
   - 注意情感基调的起承转合

【音视频协同分析指南】
- 语音与画面同步: 选择语音内容与视觉内容相互呼应的片段
- 情感一致性: 语音情感与画面情感基调保持一致
- 关键信息点: 语音中的金句、重点信息对应的画面时刻
- 节奏把控: 利用语音的停顿、转折配合视觉的场景切换

【输出格式】（严格遵循JSON格式）
请严格按照以下JSON格式输出剪辑决策，不要添加markdown代码块标记：

{{
  "theme": "{theme}",
  "total_duration": 目标总时长（秒）,
  "clips": [
    {{
      "video_id": "视频ID",
      "start_time": 起始时间（秒，浮点数）,
      "end_time": 结束时间（秒，浮点数）,
      "duration": 片段时长（秒，浮点数）,
      "reason": "选择理由：说明为什么选这个片段，包括视觉亮点和音频价值",
      "visual_highlights": "视觉精彩点描述",
      "audio_highlights": "音频精彩点描述（如有语音内容）",
      "importance_score": 重要性评分（0.0-1.0）,
      "confidence": 选择信心度（0.0-1.0）,
      "tags": ["标签1", "标签2", "标签3"]
    }}
  ],
  "editing_notes": "整体剪辑建议和注意事项"
}}

【评分标准】
- 内容相关性 (30%): 片段内容与主题"{theme}"的契合程度
- 视觉质量 (25%): 画面精彩程度、视觉冲击力
- 音频价值 (20%): 语音内容的信息量和感染力
- 情感共鸣 (15%): 能否引发观众情感反应
- 节奏把控 (10%): 片段组合的流畅度和节奏感

请基于以上视频素材的视觉分析和语音内容，生成精准的剪辑决策方案："""

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
