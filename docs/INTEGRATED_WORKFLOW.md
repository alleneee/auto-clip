# 完整视频生产工作流程

## 概述

AgnoClipTeam现在支持完整的端到端视频生产流程，从视频分析到最终带口播和字幕的成片，一键完成。

## 工作流程

### 完整的8步流程

```
Step 1: ContentAnalyzerAgent
   → 多模态视频分析（视觉+音频）

Step 2: CreativeStrategistAgent
   → 创意策略制定

Step 3: TechnicalPlannerAgent
   → 技术剪辑方案规划

Step 4: QualityReviewerAgent
   → 质量评审（支持迭代改进）

Step 5: VideoExecutorAgent (可选)
   → 执行视频剪辑
   → 输出: clipped_video.mp4

Step 6: ScriptGeneratorAgent (可选)
   → 基于剪辑内容生成口播脚本
   → 输出: ScriptGeneration对象

Step 7: ScriptGeneratorAgent (可选，异步)
   → 并行生成TTS音频
   → 输出: TTSGenerationResult对象

Step 8: VideoExecutorAgent (可选)
   → 替换视频音频为TTS
   → 烧录字幕或生成SRT文件
   → 输出: final_video.mp4 + subtitles.srt
```

## 使用方法

### 基础用法（仅生成方案）

```python
from app.agents.clip_team import AgnoClipTeam

# 创建团队（默认只生成方案，不执行）
team = AgnoClipTeam(
    analyzer_model="qwen-vl-plus",
    analyzer_provider="dashscope",
    strategist_model="qwen-max",
    planner_model="qwen-max",
    reviewer_model="qwen-max",
    text_provider="qwen"
)

# 运行（同步）
result = await team.run(
    video_paths=["video1.mp4", "video2.mp4"],
    config={"target_duration": 60, "platform": "douyin"}
)

# 获取方案
print(result.technical_plan.segments)
```

### 完整用法（生成带口播和字幕的视频）

```python
import asyncio
from app.agents.clip_team import AgnoClipTeam

async def main():
    # 创建团队（启用所有功能）
    team = AgnoClipTeam(
        analyzer_model="qwen-vl-plus",
        analyzer_provider="dashscope",
        strategist_model="qwen-max",
        planner_model="qwen-max",
        reviewer_model="qwen-max",
        script_model="qwen-max",
        text_provider="qwen",
        enable_video_execution=True,  # ✅ 启用视频剪辑
        enable_narration=True,        # ✅ 启用口播和字幕
        temp_dir="./tmp"
    )

    # 配置参数
    config = {
        "target_duration": 30,
        "platform": "douyin",
        "narration_voice": "Cherry",  # TTS音色
        "generate_srt": True,          # 生成SRT字幕文件
        "burn_subtitles": True,        # 烧录字幕到视频
        "subtitle_config": {           # 字幕样式
            "fontsize": 48,
            "color": "white",
            "bg_color": "rgba(0,0,0,128)"
        }
    }

    # 一键执行完整流程
    result = await team.run(
        video_paths=["video1.mp4", "video2.mp4"],
        config=config,
        output_path="./output/final_video.mp4"
    )

    # 查看结果
    print(f"剪辑视频: {result.clipped_video_path}")
    print(f"最终视频: {result.final_video_path}")
    print(f"字幕文件: {result.srt_file_path}")
    print(f"脚本: {result.script.full_script}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 配置参数

### 初始化参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `analyzer_model` | str | "gemini-2.0-flash" | 视频分析模型 |
| `analyzer_provider` | str | "gemini-proxy" | 分析器Provider |
| `strategist_model` | str | "deepseek-chat" | 策略模型 |
| `planner_model` | str | "deepseek-chat" | 规划模型 |
| `reviewer_model` | str | "deepseek-chat" | 评审模型 |
| `script_model` | str | "qwen-max" | 脚本生成模型 |
| `text_provider` | str | "qwen" | 文本Provider |
| `enable_video_execution` | bool | False | 是否执行视频剪辑 |
| `enable_narration` | bool | False | 是否生成口播和字幕 |
| `temp_dir` | str | None | 临时文件目录 |

### run()配置参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `target_duration` | int | 60 | 目标时长（秒） |
| `platform` | str | "douyin" | 平台 |
| `narration_voice` | str | "Cherry" | TTS音色 |
| `generate_srt` | bool | True | 是否生成SRT字幕文件 |
| `burn_subtitles` | bool | True | 是否烧录字幕到视频 |
| `subtitle_config` | dict | {...} | 字幕样式配置 |

### 字幕配置

```python
subtitle_config = {
    "fontsize": 48,              # 字号
    "color": "white",            # 文字颜色
    "bg_color": "rgba(0,0,0,128)",  # 背景颜色（半透明黑色）
    "method": "caption",         # 渲染方法
    "align": "center"            # 对齐方式
}
```

## 返回值 (AgnoClipTeamOutput)

### 核心字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `analyses` | List[MultimodalAnalysis] | 所有视频的分析结果 |
| `strategy` | CreativeStrategy | 创意策略 |
| `technical_plan` | TechnicalPlan | 技术方案 |
| `quality_review` | QualityReview | 质量评审 |

### 视频输出

| 字段 | 类型 | 说明 |
|------|------|------|
| `clipped_video_path` | str | 剪辑后视频路径（Step 5输出） |
| `final_video_path` | str | 最终视频路径（Step 8输出，带口播和字幕） |
| `video_duration` | float | 视频时长（秒） |
| `video_file_size_mb` | float | 文件大小（MB） |

### 口播和字幕

| 字段 | 类型 | 说明 |
|------|------|------|
| `script` | ScriptGeneration | 生成的口播脚本 |
| `tts_result` | TTSGenerationResult | TTS音频生成结果 |
| `srt_file_path` | str | SRT字幕文件路径 |

### 元数据

| 字段 | 类型 | 说明 |
|------|------|------|
| `total_input_videos` | int | 输入视频总数 |
| `processing_time` | float | 处理耗时（秒） |
| `iteration_count` | int | 迭代次数 |
| `final_passed` | bool | 是否通过质量评审 |

## 功能启用矩阵

| enable_video_execution | enable_narration | 执行步骤 | 输出 |
|------------------------|------------------|----------|------|
| False | False | 1-4 | 方案JSON |
| True | False | 1-5 | 剪辑视频 |
| True | True | 1-8 | 完整视频（带口播和字幕） |
| False | True | ❌ | 报错（narration需要video） |

## 使用场景

### 1. 快速方案生成
```python
# 仅生成剪辑方案，不执行
team = AgnoClipTeam()
result = await team.run(video_paths=[...], config={...})
# 输出: result.technical_plan
```

### 2. 视频剪辑
```python
# 生成剪辑视频，无口播
team = AgnoClipTeam(enable_video_execution=True)
result = await team.run(video_paths=[...], output_path="out.mp4")
# 输出: result.clipped_video_path
```

### 3. 完整视频生产
```python
# 一键生成带口播和字幕的完整视频
team = AgnoClipTeam(
    enable_video_execution=True,
    enable_narration=True
)
result = await team.run(
    video_paths=[...],
    config={
        "narration_voice": "Cherry",
        "generate_srt": True,
        "burn_subtitles": True
    },
    output_path="final.mp4"
)
# 输出:
#   - result.clipped_video_path (剪辑视频)
#   - result.final_video_path (最终视频)
#   - result.srt_file_path (字幕文件)
#   - result.script (脚本)
```

## TTS音色选项

支持qwen3-tts-flash的所有音色：

| 音色 | 说明 |
|------|------|
| Cherry | 女声（默认） |
| Peach | 女声 |
| Plum | 女声 |

## 注意事项

1. **异步执行**: `run()`方法是异步的，必须使用`await`或`asyncio.run()`
2. **依赖关系**: `enable_narration=True`要求`enable_video_execution=True`
3. **API配额**: TTS生成会消耗DashScope API配额
4. **文件管理**: 中间文件保存在`temp_dir`中，可以定期清理
5. **错误处理**: 任何步骤失败都会记录日志，后续步骤跳过

## 测试脚本

运行测试：
```bash
python test_integrated_workflow.py
```

查看完整示例：
```bash
python test_complete_narration_workflow.py
```

## 更新历史

- **v2.0**: 添加完整视频生产工作流程（Step 6-8）
- **v1.0**: 基础剪辑方案生成（Step 1-5）
