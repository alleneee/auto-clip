"""
脚本生成服务 - 基于剪辑内容生成解说词
职责: 根据视频剪辑决策和主题生成配音脚本
"""
from typing import List, Dict, Any, Optional
from app.utils.ai_clients.dashscope_client import DashScopeClient
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ScriptGenerationService:
    """脚本生成服务 - 基于剪辑内容生成配音解说词"""

    def __init__(self):
        """初始化脚本生成服务"""
        self.llm_client = DashScopeClient()

    async def generate_narration_script(
        self,
        theme: str,
        clips: List[Dict[str, Any]],
        target_duration: float,
        style: str = "professional"
    ) -> Dict[str, Any]:
        """
        基于剪辑方案生成解说脚本

        Args:
            theme: 视频主题
            clips: 剪辑片段列表，每个片段包含:
                - start_time: 开始时间
                - end_time: 结束时间
                - duration: 时长
                - reason: 选择理由
                - visual_highlights: 视觉亮点
                - audio_highlights: 音频亮点
                - tags: 标签
            target_duration: 目标总时长
            style: 解说风格 (professional/casual/enthusiastic/educational)

        Returns:
            Dict包含:
                - full_script: 完整脚本文本
                - segments: 脚本分段列表
                - total_duration: 预估总时长
                - word_count: 字数统计
        """
        try:
            logger.info(
                f"生成解说脚本: 主题={theme}, 片段数={len(clips)}, "
                f"目标时长={target_duration}秒, 风格={style}"
            )

            # 构建剪辑内容摘要
            clips_summary = self._build_clips_summary(clips)

            # 构建提示词
            prompt = self._build_script_prompt(
                theme=theme,
                clips_summary=clips_summary,
                target_duration=target_duration,
                style=style
            )

            # 调用LLM生成脚本
            script_response = await self.llm_client.chat(
                prompt=prompt,
                system_prompt=self._get_system_prompt(style)
            )

            # 解析脚本响应
            script_data = self._parse_script_response(script_response)

            # 计算脚本统计信息
            script_data['word_count'] = len(script_data['full_script'])
            script_data['estimated_duration'] = self._estimate_speech_duration(
                script_data['full_script']
            )

            logger.info(
                f"脚本生成成功: 字数={script_data['word_count']}, "
                f"预估时长={script_data['estimated_duration']:.1f}秒"
            )

            return script_data

        except Exception as e:
            logger.error(f"脚本生成失败: {str(e)}", exc_info=True)
            raise ValueError(f"生成解说脚本失败: {str(e)}")

    def _build_clips_summary(self, clips: List[Dict[str, Any]]) -> str:
        """构建剪辑内容摘要"""
        summary_parts = []

        for i, clip in enumerate(clips, 1):
            duration = clip.get('duration', 0)
            visual = clip.get('visual_highlights', '')
            reason = clip.get('reason', '')
            tags = ', '.join(clip.get('tags', []))

            summary_parts.append(
                f"片段{i} ({duration:.1f}秒):\n"
                f"  内容: {visual}\n"
                f"  选择理由: {reason}\n"
                f"  标签: {tags}"
            )

        return "\n\n".join(summary_parts)

    def _build_script_prompt(
        self,
        theme: str,
        clips_summary: str,
        target_duration: float,
        style: str
    ) -> str:
        """构建脚本生成提示词"""

        style_guidance = {
            'professional': '专业、客观、信息丰富，适合商业展示',
            'casual': '轻松、亲切、生活化，适合社交媒体',
            'enthusiastic': '热情、有感染力、激动人心，适合营销推广',
            'educational': '清晰、详细、循序渐进，适合教学讲解'
        }

        # 根据目标时长计算建议字数（中文）
        # 假设语速：3个字/秒（正常语速）
        target_words = int(target_duration * 3)

        prompt = f"""
你是一位专业的视频配音脚本撰写专家。请根据以下信息，为视频剪辑生成配音解说脚本。

【视频主题】
{theme}

【剪辑内容】
{clips_summary}

【脚本要求】
1. 风格定位: {style_guidance.get(style, '专业')}
2. 目标时长: {target_duration}秒
3. 建议字数: 约{target_words}字（语速：3字/秒）
4. 内容要求:
   - 紧扣视频主题和各片段内容
   - 突出视觉亮点，引导观众注意力
   - 保持流畅自然的叙述节奏
   - 开头要吸引人，结尾要有力
   - 避免过度描述画面，重点提炼核心信息

【输出格式】
请严格按照以下JSON格式输出，不要添加markdown代码块标记：

{{
  "full_script": "完整的配音脚本文本",
  "segments": [
    {{
      "clip_index": 1,
      "text": "该片段对应的配音文本",
      "duration_estimate": 预估朗读时长（秒）
    }}
  ],
  "script_notes": "脚本创作说明和注意事项"
}}

请开始生成配音脚本：
"""
        return prompt

    def _get_system_prompt(self, style: str) -> str:
        """获取系统提示词"""
        return (
            "你是一位资深的视频配音脚本撰写专家，擅长为各类短视频创作引人入胜的解说词。"
            "你的脚本简洁有力、节奏流畅，能够精准传达视频主题和视觉亮点。"
            "你始终确保脚本与视频内容紧密配合，避免信息冗余或偏离主题。"
        )

    def _parse_script_response(self, response: str) -> Dict[str, Any]:
        """解析脚本生成响应"""
        import json

        # 清理可能的markdown代码块
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        try:
            script_data = json.loads(response)
            return script_data
        except json.JSONDecodeError as e:
            logger.error(f"脚本JSON解析失败: {str(e)}")
            # 如果JSON解析失败，返回原始文本
            return {
                'full_script': response,
                'segments': [],
                'script_notes': '解析失败，返回原始文本'
            }

    def _estimate_speech_duration(self, text: str) -> float:
        """
        预估语音时长

        Args:
            text: 文本内容

        Returns:
            预估的朗读时长（秒）

        Note:
            中文平均语速约为3字/秒（正常语速）
            实际TTS时长可能略有差异
        """
        # 统计中文字符数
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])

        # 统计英文单词数
        import re
        english_words = len(re.findall(r'\b[a-zA-Z]+\b', text))

        # 计算时长（中文3字/秒，英文2词/秒）
        duration = chinese_chars / 3.0 + english_words / 2.0

        return duration


# 单例实例
script_generation_service = ScriptGenerationService()
