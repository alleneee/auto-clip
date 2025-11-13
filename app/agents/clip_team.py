"""
AgnoClipTeam - 智能剪辑Agent团队协调器（Workflow模式）

使用Agno Workflow编排四个Agent的步骤化执行
"""

import time
from typing import List, Dict, Any, Optional
from pathlib import Path

from agno.workflow import Workflow

from app.agents.content_analyzer import ContentAnalyzerAgent
from app.agents.creative_strategist import CreativeStrategistAgent
from app.agents.technical_planner import TechnicalPlannerAgent
from app.agents.quality_reviewer import QualityReviewerAgent
from app.agents.video_executor import VideoExecutorAgent

from app.models.agno_models import (
    AgnoClipTeamOutput,
    MultimodalAnalysis,
    CreativeStrategy,
    TechnicalPlan,
    QualityReview
)

import structlog

logger = structlog.get_logger(__name__)


class AgnoClipTeam:
    """
    Agno智能剪辑Agent团队（基于Workflow）

    使用Agno Workflow编排五个步骤：
    Step 1: ContentAnalyzerAgent - 全模态视频分析
    Step 2: CreativeStrategistAgent - 创意策略制定
    Step 3: TechnicalPlannerAgent - 技术方案规划（支持迭代）
    Step 4: QualityReviewerAgent - 质量评审把关（支持迭代）
    Step 5: VideoExecutorAgent - 视频剪辑执行（可选）
    """

    def __init__(
        self,
        analyzer_model: str = "qwen-vl-max",
        strategist_model: str = "qwen-max",
        planner_model: str = "qwen-max",
        reviewer_model: str = "qwen-max",
        script_model: str = "qwen-max",           # 新增：脚本生成模型
        analyzer_provider: str = "dashscope",  # 新增：analyzer的provider
        text_provider: str = "qwen",              # 新增：文本Agent的provider
        tts_provider: str = "edge",          # 新增：TTS提供商（dashscope/edge）
        max_iterations: int = 3,                  # 新增：最大迭代次数
        temp_dir: Optional[str] = None,           # 新增：视频剪辑临时目录
        enable_video_execution: bool = True,     # 新增：是否启用视频执行功能
        enable_narration: bool = True            # 新增：是否启用口播和字幕功能
    ):
        """
        初始化Agent团队和Workflow

        Args:
            analyzer_model: 视频分析模型名
                - gemini-proxy: "gemini-2.0-flash", "gemini-1.5-pro"
                - dashscope: "qwen-vl-plus", "qwen-vl-max"
            strategist_model: 策略制定模型名（qwen: "qwen-max", deepseek: "deepseek-chat"）
            planner_model: 技术规划模型名（qwen: "qwen-max", deepseek: "deepseek-chat"）
            reviewer_model: 质量评审模型名（qwen: "qwen-max", deepseek: "deepseek-chat"）
            analyzer_provider: 视频分析Provider（"gemini-proxy" 或 "dashscope"）
            text_provider: 文本Agent Provider（"qwen" 或 "deepseek"）
            max_iterations: 质量评审不通过时的最大重试次数（默认3次）
            temp_dir: 视频剪辑临时目录（默认使用settings.temp_dir）
            enable_video_execution: 是否启用视频执行功能（默认False，仅生成方案）

        注意：API密钥由各个Agent内部自动从配置文件或环境变量获取：
            - ContentAnalyzer: GOOGLE_API_KEY (Gemini) 或 DASHSCOPE_API_KEY (Qwen)
            - 其他Agent: DASHSCOPE_API_KEY (Qwen) 或从环境变量获取 (DeepSeek)
        """
        self.max_iterations = max_iterations
        self.enable_video_execution = enable_video_execution
        self.enable_narration = enable_narration
        self.temp_dir = temp_dir

        self.content_analyzer = ContentAnalyzerAgent(
            model=analyzer_model,
            provider=analyzer_provider
        )

        self.creative_strategist = CreativeStrategistAgent(
            model=strategist_model,
            provider=text_provider
        )

        self.technical_planner = TechnicalPlannerAgent(
            model=planner_model,
            provider=text_provider
        )

        self.quality_reviewer = QualityReviewerAgent(
            model=reviewer_model,
            provider=text_provider
        )

        # 初始化视频执行Agent（在需要执行或口播时启用）
        self.video_executor = None
        if enable_video_execution or enable_narration:
            self.video_executor = VideoExecutorAgent(
                temp_dir=temp_dir,
                default_add_transitions=True
            )

        # 初始化脚本生成Agent（可选，启用narration时需要）
        self.script_generator = None
        if enable_narration:
            from app.agents.script_generator import ScriptGeneratorAgent
            self.script_generator = ScriptGeneratorAgent(
                model=script_model,
                temperature=0.7,
                tts_provider=tts_provider
            )

        # 构建Workflow
        self.workflow = self._build_workflow()

        logger.info(
            "AgnoClipTeam初始化完成（Workflow模式）",
            analyzer_model=analyzer_model,
            analyzer_provider=analyzer_provider,
            strategist_model=strategist_model,
            planner_model=planner_model,
            reviewer_model=reviewer_model,
            text_provider=text_provider,
            video_execution_enabled=enable_video_execution
        )

    def _build_workflow(self) -> Workflow:
        """
        构建Agno Workflow

        根据enable_video_execution和enable_narration配置动态添加步骤
        """
        steps = [
            self._step_1_analyze_videos,
            self._step_2_generate_strategy,
            self._step_3_create_technical_plan,
            self._step_4_review_quality
        ]

        # 添加可选步骤
        if self.enable_video_execution:
            steps.append(self._step_5_execute_video)

        if self.enable_narration:
            steps.append(self._step_6_generate_script)
            # Note: Step 7和8需要异步处理，将在run()中特殊处理
            # Step 7: _step_7_generate_tts (async)
            # Step 8: _step_8_add_narration (depends on Step 7)

        workflow = Workflow(
            name="ClipPlanWorkflow",
            steps=steps
        )

        logger.info(
            "Workflow构建完成",
            total_steps=len(steps),
            video_execution=self.enable_video_execution,
            narration=self.enable_narration
        )
        return workflow

    # ========== Workflow Steps定义 ==========

    def _step_1_analyze_videos(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        步骤1：分析所有视频

        Args:
            context: Workflow上下文，包含video_paths

        Returns:
            更新后的上下文，添加analyses字段
        """
        logger.info("【步骤1/4】开始视频内容分析")

        video_paths = context.get("video_paths", [])
        analyses = []

        for i, video_path in enumerate(video_paths, 1):
            path = Path(video_path)
            if not path.exists():
                logger.warning(f"视频文件不存在，跳过: {video_path}")
                continue

            logger.info(f"分析视频 {i}/{len(video_paths)}: {path.name}")

            try:
                analysis = self.content_analyzer.analyze(
                    video_path=str(path),
                    video_id=path.stem
                )
                analyses.append(analysis)

            except Exception as e:
                logger.error(
                    f"视频分析失败: {path.name}",
                    error=str(e)
                )
                continue

        if not analyses:
            raise ValueError("没有成功分析的视频")

        # 更新上下文
        context["analyses"] = analyses

        logger.info(
            "【步骤1/4】视频分析完成",
            analyzed_count=len(analyses)
        )

        return context

    def _step_2_generate_strategy(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        步骤2：生成创意策略

        Args:
            context: 包含analyses和config的上下文

        Returns:
            更新后的上下文，添加strategy字段
        """
        logger.info("【步骤2/4】开始创意策略制定")

        analyses = context["analyses"]
        config = context.get("config", {})

        strategy = self.creative_strategist.generate_strategy(
            analyses=analyses,
            config=config
        )

        # 更新上下文
        context["strategy"] = strategy

        logger.info(
            "【步骤2/4】创意策略制定完成",
            style=strategy.recommended_style,
            hook=strategy.viral_hook
        )

        return context

    def _step_3_create_technical_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        步骤3：创建技术方案（支持迭代改进）

        Args:
            context: 包含analyses、strategy、config的上下文
                    可选包含previous_review（前一次评审意见）

        Returns:
            更新后的上下文，添加technical_plan字段
        """
        previous_review = context.get("previous_review")

        if previous_review:
            logger.info(
                "【步骤3/4】基于评审反馈重新规划技术方案",
                previous_score=previous_review.overall_score,
                issues=len(previous_review.feedback.improvements)
            )
        else:
            logger.info("【步骤3/4】开始技术方案规划")

        analyses = context["analyses"]
        strategy = context["strategy"]
        config = context.get("config", {})

        technical_plan = self.technical_planner.create_plan(
            analyses=analyses,
            strategy=strategy,
            config=config,
            previous_review=previous_review  # 传递评审意见
        )

        # 更新上下文
        context["technical_plan"] = technical_plan

        logger.info(
            "【步骤3/4】技术方案规划完成",
            segments=len(technical_plan.segments),
            duration=technical_plan.total_duration
        )

        return context

    def _step_4_review_quality(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        步骤4：质量评审

        Args:
            context: 包含analyses、strategy、technical_plan的上下文

        Returns:
            更新后的上下文，添加quality_review字段
        """
        logger.info("【步骤4/4】开始质量评审")

        analyses = context["analyses"]
        strategy = context["strategy"]
        technical_plan = context["technical_plan"]

        quality_review = self.quality_reviewer.review(
            analyses=analyses,
            strategy=strategy,
            plan=technical_plan
        )

        # 更新上下文
        context["quality_review"] = quality_review

        logger.info(
            "【步骤4/4】质量评审完成",
            score=quality_review.overall_score,
            passed=quality_review.pass_review
        )

        return context

    def _step_5_execute_video(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        步骤5：执行视频剪辑（可选）

        Args:
            context: 包含video_paths、technical_plan、output_path的上下文

        Returns:
            更新后的上下文，添加execution_result字段
        """
        logger.info("【步骤5/5】开始执行视频剪辑")

        if not self.video_executor:
            logger.warning("VideoExecutor未启用，跳过视频剪辑执行")
            return context

        video_paths = context.get("video_paths", [])
        technical_plan = context["technical_plan"]
        output_path = context.get("output_path")

        if not output_path:
            logger.error("未指定output_path，无法执行视频剪辑")
            return context

        try:
            # 执行剪辑
            execution_result = self.video_executor.execute_from_video_paths(
                technical_plan=technical_plan,
                video_paths=video_paths,
                output_path=output_path,
                add_transitions=True
            )

            # 更新上下文
            context["execution_result"] = execution_result

            if execution_result["success"]:
                logger.info(
                    "【步骤5/5】视频剪辑执行成功",
                    output_path=execution_result["output_path"],
                    duration=execution_result["total_duration"],
                    file_size_mb=execution_result.get("file_size_mb", 0)
                )

        except Exception as e:
            logger.error(
                "【步骤5/5】视频剪辑执行异常",
                error=str(e),
                exc_info=True
            )
            context["execution_result"] = {
                "success": False,
                "error": str(e)
            }

        return context

    def _step_6_generate_script(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        步骤6：生成口播脚本（可选）

        Args:
            context: 包含analyses、strategy、technical_plan、config的上下文

        Returns:
            更新后的上下文，添加script字段
        """
        logger.info("【步骤6/8】开始生成口播脚本")

        if not self.script_generator:
            logger.warning("ScriptGenerator未启用，跳过脚本生成")
            return context

        try:
            analyses = context["analyses"]
            strategy = context["strategy"]
            technical_plan = context["technical_plan"]
            config = context.get("config", {})

            # 生成脚本
            script = self.script_generator.generate_script(
                analyses=analyses,
                strategy=strategy,
                plan=technical_plan,
                config=config
            )

            # 根据配置覆盖TTS音色
            narration_voice = config.get("narration_voice") if config else None
            if narration_voice:
                script.tts_voice = narration_voice

            # 更新上下文
            context["script"] = script

            logger.info(
                "【步骤6/8】脚本生成成功",
                title=script.title,
                word_count=script.word_count,
                estimated_duration=script.estimated_speech_duration,
                segments=len(script.narration_segments)
            )

        except Exception as e:
            logger.error(
                "【步骤6/8】脚本生成异常",
                error=str(e),
                exc_info=True
            )
            context["script"] = None

        return context

    async def _step_7_generate_tts(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        步骤7：生成TTS音频（可选，异步）

        Args:
            context: 包含script的上下文

        Returns:
            更新后的上下文，添加tts_result字段
        """
        logger.info("【步骤7/8】开始生成TTS音频")

        if not self.script_generator:
            logger.warning("ScriptGenerator未启用，跳过TTS生成")
            return context

        script = context.get("script")
        if not script:
            logger.error("脚本为空，无法生成TTS")
            return context

        config = context.get("config", {})

        try:
            # 生成TTS音频输出目录
            import os
            from pathlib import Path
            tts_output_dir = Path(self.temp_dir or "./tmp") / "tts_audio"
            tts_output_dir.mkdir(parents=True, exist_ok=True)

            # 生成TTS
            tts_result = await self.script_generator.generate_tts_audio(
                script=script,
                output_dir=str(tts_output_dir),
                config=config
            )

            # 更新上下文
            context["tts_result"] = tts_result

            logger.info(
                "【步骤7/8】TTS生成成功",
                success_count=tts_result.success_count,
                failed_count=tts_result.failed_count,
                total_duration=tts_result.total_duration
            )

        except Exception as e:
            logger.error(
                "【步骤7/8】TTS生成异常",
                error=str(e),
                exc_info=True
            )
            context["tts_result"] = None

        return context

    def _step_8_add_narration(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        步骤8：添加口播和字幕（可选）

        Args:
            context: 包含execution_result、script、tts_result、config的上下文

        Returns:
            更新后的上下文，添加narration_result字段
        """
        logger.info("【步骤8/8】开始添加口播和字幕")

        if not self.video_executor:
            logger.warning("VideoExecutor未启用，跳过口播添加")
            return context

        execution_result = context.get("execution_result")
        script = context.get("script")
        tts_result = context.get("tts_result")
        config = context.get("config", {})

        clipped_video_path = None
        if execution_result and execution_result.get("success"):
            clipped_video_path = execution_result["output_path"]
        else:
            fallback_video_path = config.get("narration_base_video")
            if fallback_video_path and Path(fallback_video_path).exists():
                clipped_video_path = fallback_video_path
                logger.info(
                    "使用外部提供的视频作为口播基准",
                    video_path=clipped_video_path
                )
            else:
                logger.error("视频剪辑未成功且未提供narration_base_video，无法添加口播")
                return context

        if not script or not tts_result:
            logger.error("脚本或TTS结果为空，无法添加口播")
            return context

        try:
            # 生成最终视频路径
            from pathlib import Path
            clipped_path = Path(clipped_video_path)
            final_video_path = str(clipped_path.parent / f"final_{clipped_path.name}")

            subtitle_defaults = {
                "fontsize": 48,
                "color": "white",
                "bg_color": "rgba(0,0,0,128)",
                "method": "caption",
                "align": "center",
                "font": [
                    "STHeiti-Medium",
                    "SimHei",
                    "SourceHanSansSC-Regular",
                    "NotoSansCJK-Regular",
                    "Arial Unicode MS"
                ]
            }
            user_subtitle = config.get("subtitle_config", {}) or {}
            normalized_subtitle = dict(user_subtitle)
            if "font_size" in normalized_subtitle and "fontsize" not in normalized_subtitle:
                normalized_subtitle["fontsize"] = normalized_subtitle.pop("font_size")
            if "font_color" in normalized_subtitle and "color" not in normalized_subtitle:
                normalized_subtitle["color"] = normalized_subtitle.pop("font_color")
            subtitle_config = {**subtitle_defaults, **normalized_subtitle}

            # 添加口播和字幕
            narration_result = self.video_executor.add_narration_and_subtitles(
                video_path=clipped_video_path,
                script=script,
                tts_result=tts_result,
                output_path=final_video_path,
                subtitle_config=subtitle_config,
                generate_srt=config.get("generate_srt", True),
                burn_subtitles=config.get("burn_subtitles", True)
            )

            # 更新上下文
            context["narration_result"] = narration_result

            if narration_result["success"]:
                logger.info(
                    "【步骤8/8】口播和字幕添加成功",
                    output_path=narration_result["output_path"],
                    has_audio=narration_result.get("has_audio"),
                    has_burned_subtitles=narration_result.get("has_burned_subtitles"),
                    srt_path=narration_result.get("srt_path")
                )

        except Exception as e:
            logger.error(
                "【步骤8/8】添加口播和字幕异常",
                error=str(e),
                exc_info=True
            )
            context["narration_result"] = {
                "success": False,
                "error": str(e)
            }

        return context

    # ========== 主执行方法 ==========

    async def run(
        self,
        video_paths: List[str],
        config: Optional[Dict[str, Any]] = None,
        output_path: Optional[str] = None
    ) -> AgnoClipTeamOutput:
        """
        运行完整的剪辑策略生成Workflow（异步）

        Args:
            video_paths: 视频文件路径列表
            config: 配置参数
                - target_duration: 目标时长（秒），默认60
                - platform: 平台（douyin/youtube/instagram），默认douyin
                - narration_voice: TTS音色（默认Cherry）
                - generate_srt: 是否生成SRT字幕文件（默认True）
                - burn_subtitles: 是否烧录字幕到视频（默认True）
                - subtitle_config: 字幕样式配置
            output_path: 最终视频输出路径（仅在enable_video_execution=True时有效）

        Returns:
            AgnoClipTeamOutput对象，包含完整的分析、策略、方案、评审和视频（可选）
        """
        start_time = time.time()

        # 默认配置
        config = config or {}
        config.setdefault("target_duration", 60)
        config.setdefault("platform", "douyin")

        logger.info(
            "开始运行AgnoClipTeam Workflow",
            videos_count=len(video_paths),
            target_duration=config["target_duration"],
            platform=config["platform"]
        )

        try:
            # 初始化Workflow上下文
            initial_context = {
                "video_paths": video_paths,
                "config": config,
                "output_path": output_path
            }

            # 执行Workflow（Step 1-6同步执行）
            final_context = self._run_workflow_steps(initial_context)

            # Step 7: 异步执行TTS生成（如果启用了narration）
            if self.enable_narration and final_context.get("script"):
                logger.info("【步骤7/8】异步执行TTS生成")
                final_context = await self._step_7_generate_tts(final_context)

            # Step 8: 添加口播和字幕（在TTS完成后）
            if self.enable_narration and final_context.get("tts_result"):
                logger.info("【步骤8/8】执行口播和字幕添加")
                final_context = self._step_8_add_narration(final_context)

            # 提取结果
            analyses = final_context["analyses"]
            strategy = final_context["strategy"]
            technical_plan = final_context["technical_plan"]
            quality_review = final_context["quality_review"]
            execution_result = final_context.get("execution_result")
            script = final_context.get("script")
            tts_result = final_context.get("tts_result")
            narration_result = final_context.get("narration_result")

            # 计算总耗时
            processing_time = time.time() - start_time

            # 确定最终视频路径
            clipped_video_path = None
            if execution_result and execution_result.get("success"):
                clipped_video_path = execution_result["output_path"]
            elif config.get("narration_base_video"):
                clipped_video_path = config["narration_base_video"]
            final_video_path = narration_result["output_path"] if narration_result and narration_result.get("success") else clipped_video_path
            srt_file_path = narration_result.get("srt_path") if narration_result else None

            # 构建最终输出
            output = AgnoClipTeamOutput(
                analyses=analyses,
                strategy=strategy,
                technical_plan=technical_plan,
                quality_review=quality_review,
                total_input_videos=len(video_paths),
                processing_time=processing_time,
                iteration_count=final_context.get("iteration_count", 1),
                final_passed=final_context.get("final_passed", quality_review.pass_review),
                clipped_video_path=clipped_video_path,
                final_video_path=final_video_path,
                video_duration=execution_result.get("total_duration") if execution_result else None,
                video_file_size_mb=execution_result.get("file_size_mb") if execution_result else None,
                script=script,
                tts_result=tts_result,
                srt_file_path=srt_file_path
            )

            logger.info(
                "AgnoClipTeam Workflow执行完成",
                total_time=f"{processing_time:.1f}秒",
                final_score=quality_review.overall_score,
                passed=quality_review.pass_review
            )

            return output

        except Exception as e:
            logger.error(
                "AgnoClipTeam Workflow执行失败",
                error=str(e),
                error_type=type(e).__name__,
                elapsed_time=f"{time.time() - start_time:.1f}秒"
            )
            raise

    def _run_workflow_steps(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行Workflow的所有步骤（支持迭代改进）

        步骤1和2只执行一次（视频分析、创意策略）
        步骤3和4支持迭代改进（技术方案、质量评审）
        如果评审不通过，最多重试 max_iterations 次

        Args:
            context: 初始上下文

        Returns:
            最终上下文（包含所有步骤的结果）
        """
        current_context = context

        # 步骤1: 视频分析（只执行一次）
        logger.debug("执行步骤 1/4: 视频分析")
        current_context = self._step_1_analyze_videos(current_context)

        # 步骤2: 创意策略（只执行一次）
        logger.debug("执行步骤 2/4: 创意策略")
        current_context = self._step_2_generate_strategy(current_context)

        # 步骤3和4: 技术方案 + 质量评审（支持迭代）
        iteration = 0
        previous_review = None

        while iteration < self.max_iterations:
            iteration += 1

            logger.info(
                f"开始迭代 {iteration}/{self.max_iterations}",
                has_previous_feedback=previous_review is not None
            )

            # 步骤3: 技术方案（传递前一次评审意见）
            logger.debug(f"执行步骤 3/4: 技术方案（迭代{iteration}）")
            current_context["previous_review"] = previous_review
            current_context = self._step_3_create_technical_plan(current_context)

            # 步骤4: 质量评审
            logger.debug(f"执行步骤 4/4: 质量评审（迭代{iteration}）")
            current_context = self._step_4_review_quality(current_context)

            quality_review = current_context["quality_review"]

            # 检查是否通过评审
            if quality_review.pass_review:
                logger.info(
                    f"✅ 质量评审通过！迭代{iteration}次成功",
                    score=quality_review.overall_score
                )
                break
            else:
                logger.warning(
                    f"❌ 质量评审未通过（迭代{iteration}/{self.max_iterations}）",
                    score=quality_review.overall_score,
                    issues_count=len(quality_review.feedback.improvements)
                )

                # 如果还有重试机会，记录评审意见用于下次迭代
                if iteration < self.max_iterations:
                    previous_review = quality_review
                    logger.info(
                        "准备重新生成技术方案",
                        revision_suggestions=quality_review.revision_suggestions
                    )
                else:
                    logger.error(
                        f"已达到最大迭代次数（{self.max_iterations}），评审仍未通过",
                        final_score=quality_review.overall_score
                    )

        # 记录最终迭代统计
        current_context["iteration_count"] = iteration
        current_context["final_passed"] = quality_review.pass_review

        # 步骤5: 视频剪辑执行（可选）
        if self.enable_video_execution:
            logger.debug("执行步骤 5/5: 视频剪辑执行")
            current_context = self._step_5_execute_video(current_context)

        # 步骤6: 脚本生成（可选）
        if self.enable_narration:
            logger.debug("执行步骤 6/8: 脚本生成")
            current_context = self._step_6_generate_script(current_context)

        return current_context


# 便捷函数
def create_clip_team(**kwargs) -> AgnoClipTeam:
    """创建AgnoClipTeam实例（Workflow模式）"""
    return AgnoClipTeam(**kwargs)
