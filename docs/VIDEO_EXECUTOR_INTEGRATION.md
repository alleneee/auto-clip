# VideoExecutorAgent 集成文档

## 概述

`VideoExecutorAgent` 已成功集成到 `AgnoClipTeam` 作为可选的第5步，实现了从 AI 分析到实际视频生成的完整一体化工作流。

## 集成架构

### 5步工作流

1. **步骤1**: ContentAnalyzer - 视频内容分析
2. **步骤2**: CreativeStrategist - 创意策略制定
3. **步骤3**: TechnicalPlanner - 技术方案规划（可迭代）
4. **步骤4**: QualityReviewer - 质量评审（可触发迭代）
5. **步骤5**: VideoExecutor - 实际视频生成（可选）⭐ **NEW**

### 关键特性

- ✅ **可选启用**: 通过 `enable_video_execution` 参数控制
- ✅ **条件触发**: 只有提供 `output_path` 时才执行视频生成
- ✅ **无缝集成**: 自动传递 `technical_plan` 和 `video_paths`
- ✅ **结果返回**: 视频路径、时长、文件大小等信息包含在输出模型中

## 使用方式

### 方式1：仅 AI 分析（4步）

```python
from app.agents.clip_team import AgnoClipTeam

# 创建团队（不启用视频执行）
team = AgnoClipTeam(
    enable_video_execution=False  # 默认值
)

# 运行（不提供 output_path）
result = team.run(
    video_paths=["video.mp4"],
    config={"target_duration": 30}
)

# 结果：只有 AI 分析和规划，没有实际视频
print(result.technical_plan)  # 有技术方案
print(result.final_video_path)  # None（未生成视频）
```

### 方式2：完整流程（5步）⭐ **推荐**

```python
from app.agents.clip_team import AgnoClipTeam

# 创建团队（启用视频执行）
team = AgnoClipTeam(
    temp_dir="/tmp/videos",
    enable_video_execution=True  # 启用视频执行
)

# 运行（提供 output_path）
result = team.run(
    video_paths=["video.mp4"],
    config={"target_duration": 30},
    output_path="/output/final.mp4"  # 触发视频生成
)

# 结果：包含 AI 分析、规划和实际视频
print(result.technical_plan)  # 有技术方案
print(result.final_video_path)  # "/output/final.mp4"
print(result.video_duration)  # 实际时长（秒）
print(result.video_file_size_mb)  # 文件大小（MB）
```

### 方式3：两步手动流程（向后兼容）

```python
from app.agents.clip_team import AgnoClipTeam
from app.agents.video_executor import VideoExecutorAgent

# 步骤1: 生成 AI 方案
team = AgnoClipTeam()
result = team.run(
    video_paths=["video.mp4"],
    config={"target_duration": 30}
)

# 步骤2: 手动执行视频生成
executor = VideoExecutorAgent()
video_result = executor.execute_from_video_paths(
    technical_plan=result.technical_plan,
    video_paths=["video.mp4"],
    output_path="/output/final.mp4"
)
```

## 代码变更

### 1. AgnoClipTeamOutput 模型扩展

文件: `app/models/agno_models.py`

```python
class AgnoClipTeamOutput(BaseModel):
    # 现有字段...
    analyses: List[MultimodalAnalysis]
    strategy: CreativeStrategy
    technical_plan: TechnicalPlan
    quality_review: QualityReview

    # 新增：视频执行结果（可选）
    final_video_path: Optional[str] = Field(default=None, description="最终视频文件路径")
    video_duration: Optional[float] = Field(default=None, ge=0, description="最终视频时长（秒）")
    video_file_size_mb: Optional[float] = Field(default=None, ge=0, description="文件大小（MB）")
```

### 2. AgnoClipTeam 参数扩展

文件: `app/agents/clip_team.py`

```python
class AgnoClipTeam:
    def __init__(
        self,
        # ... 现有参数 ...
        temp_dir: Optional[str] = None,           # NEW
        enable_video_execution: bool = False      # NEW
    ):
        # 初始化 VideoExecutor（如果启用）
        self.video_executor = None
        if enable_video_execution:
            self.video_executor = VideoExecutorAgent(
                temp_dir=temp_dir,
                default_add_transitions=True
            )

    def run(
        self,
        video_paths: List[str],
        config: Optional[Dict[str, Any]] = None,
        output_path: Optional[str] = None  # NEW: 触发视频生成
    ) -> AgnoClipTeamOutput:
        # ... 执行步骤 1-4 ...

        # 步骤5: 视频执行（如果启用且提供 output_path）
        if self.enable_video_execution and output_path:
            context = self._step_5_execute_video(context)

        # 构建输出
        execution_result = context.get("execution_result")
        return AgnoClipTeamOutput(
            # ... 现有字段 ...
            final_video_path=execution_result["output_path"] if execution_result and execution_result.get("success") else None,
            video_duration=execution_result.get("total_duration") if execution_result else None,
            video_file_size_mb=execution_result.get("file_size_mb") if execution_result else None
        )
```

### 3. 第5步实现

文件: `app/agents/clip_team.py`

```python
def _step_5_execute_video(self, context: Dict[str, Any]) -> Dict[str, Any]:
    """步骤5：执行视频剪辑（可选）"""
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

        context["execution_result"] = execution_result

        if execution_result["success"]:
            logger.info(
                "【步骤5/5】视频剪辑执行成功",
                output_path=execution_result["output_path"],
                duration=execution_result["total_duration"]
            )
        else:
            logger.error("【步骤5/5】视频剪辑执行失败", error=execution_result.get("error"))

    except Exception as e:
        logger.error("【步骤5/5】视频剪辑执行异常", error=str(e))
        context["execution_result"] = {"success": False, "error": str(e)}

    return context
```

## 调试功能

### Agent 响应打印

所有 4 个 Agent 现在都会打印完整的原始响应内容：

1. **ContentAnalyzer**: 打印每个视频的分析结果
2. **CreativeStrategist**: 打印创意策略详情
3. **TechnicalPlanner**: 打印技术方案和片段列表
4. **QualityReviewer**: 打印质量评分和反馈

文件位置：
- `app/agents/content_analyzer.py:297-301`
- `app/agents/creative_strategist.py:287-291`
- `app/agents/technical_planner.py:288-292`
- `app/agents/quality_reviewer.py:254-258`

### ClipTeam 步骤摘要

`AgnoClipTeam` 在每个步骤完成后打印处理后的摘要信息：

文件位置: `app/agents/clip_team.py`
- 步骤1摘要: 行 197-209
- 步骤2摘要: 行 243-260
- 步骤3摘要: 行 307-322
- 步骤4摘要: 行 358-381
- 步骤5摘要: 行 430-456

## 测试

### 快速验证测试

```bash
python test_verify_integration.py
```

这个测试会运行两种模式：
1. 模式1: 仅 AI 分析（4步）
2. 模式2: 完整流程（5步，含视频生成）

### 端到端测试

```bash
python test_end_to_end_video.py
```

提供交互式选择：
- 方式1（旧）: 两步流程
- 方式2（新）: 一步流程（推荐）
- 运行两个测试对比

## 优势

### 一体化工作流
- 从 AI 分析到视频生成一步完成
- 减少中间数据传递和状态管理

### 灵活控制
- 可以选择仅 AI 分析或完整流程
- 根据需求动态决定是否生成视频

### 向后兼容
- 不影响现有代码
- 默认行为不变（enable_video_execution=False）

### 统一输出
- 所有结果统一在 `AgnoClipTeamOutput` 中
- 简化结果访问和处理

## 工具实现参考

VideoExecutor 使用的工具实现：

### VideoEditingTools (Toolkit 类)

文件: `app/tools/video_editing_tool.py`

- 继承自 `agno.tools.Toolkit`
- 方法返回 JSON 字符串
- 支持 `include_tools`/`exclude_tools` 过滤

核心方法：
- `extract_clip()`: 提取视频片段
- `concatenate_clips()`: 拼接视频
- `get_video_info_tool()`: 获取视频信息
- `execute_clip_plan()`: 执行完整剪辑方案

### @tool 装饰器实现（备选）

文件: `app/tools/video_editing_decorators.py`

- 使用 `@tool` 装饰器标记函数
- 更简洁，适合快速开发

详细文档: `docs/VIDEO_EDITING_TOOLS_IMPLEMENTATION.md`

## 相关文档

- `docs/MOVIEPY_2X_METHODS.md` - MoviePy 2.x API 参考
- `docs/VIDEO_EDITING_TOOLS_IMPLEMENTATION.md` - 工具实现详解
- `docs/AGNO_AGENT_SYSTEM.md` - Agno Agent 系统概述
- `test_video_editing_tools.py` - 工具测试脚本

## 版本历史

- **v1.0** (2025-11-12): VideoExecutorAgent 作为第5步集成到 AgnoClipTeam
  - 新增 `enable_video_execution` 参数
  - 新增 `output_path` 参数到 `run()` 方法
  - 扩展 `AgnoClipTeamOutput` 模型
  - 添加完整的调试日志和响应打印
