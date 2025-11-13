"""
ScriptGeneratorAgent - 脚本生成师

基于视频分析、创意策略和剪辑方案，生成对应的口播文案
"""

import json
import asyncio
from typing import Dict, Any, List, Literal, Optional
from pathlib import Path
from agno.agent import Agent
from agno.models.dashscope import DashScope

from app.models.agno_models import (
    MultimodalAnalysis,
    CreativeStrategy,
    TechnicalPlan,
    ScriptGeneration,
    NarrationSegment,
    TTSGenerationResult,
    TTSSegmentAudio
)
from app.adapters.tts_adapters import DashScopeTTSAdapter
from app.adapters.edge_tts_adapter import EdgeTTSAdapter
from app.adapters.kokoro_tts_adapter import KokoroTTSAdapter
from app.config import settings
import structlog

logger = structlog.get_logger(__name__)


class ScriptGeneratorAgent:
    """
    脚本生成师Agent

    职责：
    - 基于剪辑方案生成分段口播文案
    - 调用TTS生成语音
    - 规划字幕时间轴
    """

    def __init__(
        self,
        model: str = "qwen-max",
        api_key: str = None,
        temperature: float = 0.7,
        provider: Literal["qwen"] = "qwen",
        tts_provider: Optional[Literal["dashscope", "edge", "kokoro"]] = None
    ):
        """
        初始化脚本生成师Agent

        Args:
            model: 模型名称（qwen-max, qwen-plus, qwen-turbo）
            api_key: API密钥（DashScope）
            temperature: 温度参数（创意文案建议0.7-0.9）
            provider: 提供商（目前只支持qwen）
        """
        self.model_name = model
        self.provider = provider

        model_instance = DashScope(
            id=model,
            api_key=api_key or settings.DASHSCOPE_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            temperature=temperature
        )

        # 创建Agno Agent
        self.agent = Agent(
            name="ScriptGenerator",
            model=model_instance,
            description="视频口播文案创作专家，擅长抖音、小红书等平台的文案风格",
            instructions=[
                "你是资深的短视频文案创作专家，擅长抖音、小红书、B站等平台的口播风格",
                "文案必须精炼、口语化、有节奏感，符合短视频快速传播的特点",
                "开场3秒的钩子文案至关重要：要么抛出悬念，要么直击痛点，要么展示冲击力画面",
                "文案要与视频内容精准匹配：每个片段的文案都要呼应该片段的视觉和音频内容",
                "控制语速：平均每秒3-4个汉字，确保观众能听清",
                "输出必须是严格的JSON格式，符合ScriptGeneration数据模型",
                "文案风格要契合视频主题和目标平台"
            ],
            markdown=False
        )

        # 初始化TTS适配器（支持多Provider）
        # 如果未指定provider，则使用配置文件中的默认值
        self.default_tts_provider = tts_provider or settings.TTS_PROVIDER
        self.tts_adapters: Dict[str, Any] = {
            "dashscope": DashScopeTTSAdapter(api_key=api_key or settings.DASHSCOPE_API_KEY)
        }
        try:
            self.tts_adapters["edge"] = EdgeTTSAdapter()
        except Exception as exc:
            logger.warning("Edge TTS初始化失败", error=str(exc))

        try:
            self.tts_adapters["kokoro"] = KokoroTTSAdapter()
        except Exception as exc:
            logger.warning("Kokoro TTS初始化失败", error=str(exc), hint="pip install kokoro>=0.9.4 soundfile")

        logger.info(
            "ScriptGeneratorAgent初始化",
            model=model,
            temperature=temperature,
            provider=provider,
            tts_provider=self.default_tts_provider
        )

    def _build_script_prompt(
        self,
        analyses: List[MultimodalAnalysis],
        strategy: CreativeStrategy,
        plan: TechnicalPlan,
        config: Dict[str, Any]
    ) -> str:
        """
        构建脚本生成提示词

        Args:
            analyses: 所有视频的分析结果
            strategy: 创意策略
            plan: 技术剪辑方案
            config: 用户配置

        Returns:
            完整的脚本提示词
        """
        platform = config.get("platform", "douyin")
        target_duration = plan.total_duration

        # 汇总剪辑片段信息
        segments_info = []
        for i, segment in enumerate(plan.segments):
            # 找到对应的分析结果
            analysis = next((a for a in analyses if a.video_id == segment.video_id), None)
            if not analysis:
                continue

            # 找到该时间段的视觉和音频描述
            visual_desc = ""
            audio_desc = ""
            for timeline_seg in analysis.timeline:
                if (segment.start_time >= timeline_seg.start and
                    segment.end_time <= timeline_seg.end):
                    visual_desc = timeline_seg.visual
                    audio_desc = timeline_seg.audio
                    break

            segments_info.append({
                "index": i,
                "role": segment.role,
                "duration": segment.duration,
                "visual": visual_desc or "（画面内容）",
                "audio": audio_desc or "（音频内容）",
                "reason": segment.reason
            })

        prompt = f"""
基于以下视频剪辑方案，为每个片段创作对应的口播文案。

**视频主题**: {strategy.theme}
**叙事结构**: {strategy.narrative_structure}
**病毒式钩子**: {strategy.viral_hook}
**视频风格**: {strategy.recommended_style}
**目标平台**: {platform}
**总时长**: {target_duration:.1f}秒

**剪辑片段详情**:
{json.dumps(segments_info, ensure_ascii=False, indent=2)}

**文案创作要求**:

1. **标题**（title）:
   - 10-20字的短视频标题
   - 包含关键词，吸引点击

2. **开场钩子**（hook_line）:
   - 前3秒的黄金钩子文案（约10-15字）
   - 必须与第一个片段的视觉内容强相关
   - 使用{strategy.viral_hook}的钩子技巧

3. **分段文案**（narration_segments）:
   为每个剪辑片段创作对应的口播文案：

   - **segment_index**: 片段索引（0, 1, 2...）
   - **start_time / end_time / duration**: 与剪辑片段完全一致
   - **text**: 该片段的口播文案
     * 文案必须与该片段的visual和audio内容紧密呼应
     * 语速控制：每秒3-4个汉字（例如3秒片段约10-12字）
     * 口语化、节奏感强、易于理解
   - **purpose**: 该段文案的作用（例如："开场引入"、"解释操作"、"展示效果"、"总结收尾"）

4. **完整文案**（full_script）:
   - 所有分段文案的完整拼接
   - 确保整体连贯、节奏流畅

5. **字数统计**（word_count）:
   - 总字数（汉字）

6. **预估语音时长**（estimated_speech_duration）:
   - 按每秒3.5字估算
   - 应该接近视频总时长{target_duration:.1f}秒

7. **风格说明**（style_notes）:
   - 描述文案的整体风格特点

**输出格式**（严格JSON）:
```json
{{
  "title": "10-20字的吸引人标题",
  "hook_line": "前3秒黄金钩子文案",
  "narration_segments": [
    {{
      "segment_index": 0,
      "start_time": 0.0,
      "end_time": 3.5,
      "duration": 3.5,
      "text": "约12字的开场文案",
      "purpose": "开场引入"
    }},
    {{
      "segment_index": 1,
      "start_time": 3.5,
      "end_time": 7.0,
      "duration": 3.5,
      "text": "约12字的主体文案",
      "purpose": "解释操作"
    }}
  ],
  "full_script": "完整文案拼接",
  "word_count": 48,
  "estimated_speech_duration": {target_duration:.1f},
  "style_notes": "口语化、节奏明快、富有感染力",
  "tts_voice": "longxiaochun",
  "tts_speed": 1.0
}}
```

**重要约束**:
- 每个片段的文案长度必须匹配该片段的时长（语速每秒3-4字）
- 文案要与视觉内容精准呼应，不要说无关的内容
- 保持口语化，避免书面语
- 开场钩子要足够吸引人，符合病毒式传播逻辑
- 只返回JSON，不要有任何其他文字
"""
        return prompt.strip()

    def generate_script(
        self,
        analyses: List[MultimodalAnalysis],
        strategy: CreativeStrategy,
        plan: TechnicalPlan,
        config: Dict[str, Any]
    ) -> ScriptGeneration:
        """
        生成脚本文案

        Args:
            analyses: 所有视频的分析结果
            strategy: 创意策略
            plan: 技术剪辑方案
            config: 用户配置

        Returns:
            ScriptGeneration对象
        """
        logger.info(
            "开始生成脚本文案",
            segments_count=len(plan.segments),
            total_duration=plan.total_duration
        )

        # 构建提示词
        prompt = self._build_script_prompt(analyses, strategy, plan, config)

        # 调用Agent
        try:
            response = self.agent.run(prompt)
            content = response.content if hasattr(response, 'content') else str(response)

            logger.info("脚本生成Agent响应", content_preview=content[:200])

            # 解析JSON
            script_data = self._parse_json_response(content)

            # 验证并转换为Pydantic模型
            script = ScriptGeneration(**script_data)

            # 覆盖TTS配置（如果调用方有自定义）
            narration_voice = config.get("narration_voice") if config else None
            if narration_voice:
                script.tts_voice = narration_voice
            tts_speed = config.get("narration_speed") if config else None
            if isinstance(tts_speed, (int, float)) and 0.5 <= tts_speed <= 2.0:
                script.tts_speed = tts_speed

            logger.info(
                "脚本生成完成",
                title=script.title,
                word_count=script.word_count,
                segments_count=len(script.narration_segments)
            )

            return script

        except Exception as e:
            logger.error(
                "脚本生成失败",
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    async def generate_tts_audio(
        self,
        script: ScriptGeneration,
        output_dir: str,
        config: Optional[Dict[str, Any]] = None
    ) -> TTSGenerationResult:
        """
        生成TTS语音（异步并行）

        Args:
            script: 脚本文案
            output_dir: 输出目录

        Returns:
            TTSGenerationResult对象
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        narration_voice = script.tts_voice
        narration_rate = script.tts_speed
        narration_pitch = None
        narration_volume = None
        narration_sample_rate = None
        narration_format = "mp3"
        narration_style = None
        narration_style_degree = None
        tts_provider = self.default_tts_provider

        if config:
            narration_voice = config.get("narration_voice", narration_voice)
            narration_rate = config.get("narration_rate", narration_rate)
            narration_pitch = config.get("narration_pitch")
            narration_volume = config.get("narration_volume")
            narration_sample_rate = config.get("narration_sample_rate")
            narration_format = config.get("narration_audio_format", narration_format)
            narration_style = config.get("narration_style")
            narration_style_degree = config.get("narration_style_degree")
            tts_provider = config.get("narration_tts_provider", tts_provider)

        tts_provider = (tts_provider or self.default_tts_provider).lower()
        adapter = self.tts_adapters.get(tts_provider)
        if not adapter:
            raise RuntimeError(f"未找到TTS Provider: {tts_provider}")

        logger.info(
            "开始生成TTS语音",
            segments_count=len(script.narration_segments),
            voice=narration_voice,
            output_dir=output_dir,
            format=narration_format,
            sample_rate=narration_sample_rate,
            provider=tts_provider
        )

        # 并行生成所有片段的TTS
        tasks = []
        for segment in script.narration_segments:
            audio_filename = (
                f"narration_{segment.segment_index}_{segment.start_time:.1f}_{segment.end_time:.1f}.{narration_format}"
            )
            audio_path = str(output_path / audio_filename)

            task = self._generate_single_tts(
                text=segment.text,
                output_path=audio_path,
                voice=narration_voice,
                rate=narration_rate,
                pitch=narration_pitch,
                volume=narration_volume,
                sample_rate=narration_sample_rate,
                audio_format=narration_format,
                style=narration_style,
                style_degree=narration_style_degree,
                adapter=adapter,
                segment_index=segment.segment_index,
                start_time=segment.start_time,
                end_time=segment.end_time
            )
            tasks.append(task)

        # 等待所有TTS生成完成
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 统计结果
        success_segments = []
        failed_count = 0

        for result in results:
            if isinstance(result, Exception):
                logger.error("TTS生成失败", error=str(result))
                failed_count += 1
            else:
                success_segments.append(result)

        # 计算总时长
        total_duration = sum(seg.duration for seg in success_segments)

        tts_result = TTSGenerationResult(
            segments=success_segments,
            total_duration=total_duration,
            success_count=len(success_segments),
            failed_count=failed_count
        )

        logger.info(
            "TTS生成完成",
            success_count=len(success_segments),
            failed_count=failed_count,
            total_duration=total_duration
        )

        return tts_result

    async def _generate_single_tts(
        self,
        text: str,
        output_path: str,
        voice: str,
        rate: Optional[float | str],
        pitch: Optional[float | str],
        volume: Optional[int | float | str],
        sample_rate: Optional[int],
        audio_format: str,
        style: Optional[str],
        style_degree: Optional[float],
        adapter: Any,
        segment_index: int,
        start_time: float,
        end_time: float
    ) -> TTSSegmentAudio:
        """生成单个片段的TTS"""
        try:
            # 调用TTS API
            await adapter.synthesize_to_file(
                text=text,
                output_path=output_path,
                voice=voice,
                output_format=audio_format,
                sample_rate=sample_rate,
                rate=rate,
                pitch=pitch,
                volume=volume,
                style=style,
                style_degree=style_degree
            )

            # 获取音频时长（使用moviepy 2.x）
            try:
                from moviepy import AudioFileClip
            except ImportError as exc:
                raise RuntimeError(
                    "MoviePy导入失败，请确保已安装 moviepy>=2.0: pip install moviepy"
                ) from exc

            audio_clip = AudioFileClip(output_path)
            duration = audio_clip.duration
            audio_clip.close()

            actual_end_time = start_time + duration

            logger.info(
                "TTS片段生成成功",
                segment_index=segment_index,
                start_time=start_time,
                end_time=actual_end_time,
                text_length=len(text),
                duration=duration,
                output_path=output_path
            )

            return TTSSegmentAudio(
                segment_index=segment_index,
                start_time=start_time,
                end_time=actual_end_time,
                audio_path=output_path,
                duration=duration,
                text=text,
                voice=voice
            )

        except Exception as e:
            logger.error(
                "TTS片段生成失败",
                segment_index=segment_index,
                error=str(e)
            )
            raise

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """解析JSON响应"""
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
            # 尝试修复常见问题
            content = content.replace("'", '"')
            content = content.rstrip(',')
            try:
                data = json.loads(content)
                logger.info("JSON修复成功")
                return data
            except:
                raise ValueError(f"无法解析JSON响应: {e}")


# 便捷函数
def create_script_generator(
    model: str = "qwen-max",
    **kwargs
) -> ScriptGeneratorAgent:
    """创建ScriptGeneratorAgent实例"""
    return ScriptGeneratorAgent(model=model, **kwargs)
