# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Auto-Clip 是一个AI驱动的智能视频剪辑平台，支持多视频导入、自动内容分析和精彩片段提取。

**技术栈**: FastAPI + Celery + Redis + MoviePy 2.x + 阿里云DashScope AI

## Development Commands

### Running the Application

```bash
# Docker方式（推荐）
docker-compose up -d              # 启动所有服务
docker-compose logs -f api        # 查看API日志
docker-compose logs -f worker-analyzer  # 查看Worker日志
docker-compose down               # 停止服务

# 本地开发方式
python -m app.main               # 启动FastAPI服务器（端口8000）
celery -A app.workers.celery_app worker -l info  # 启动Celery Worker
redis-server                     # 启动Redis（需单独安装）
```

### Testing

```bash
# 运行所有测试
pytest tests/

# 运行特定测试文件
pytest tests/test_utils.py

# 运行带详细输出的测试
pytest tests/ -v

# 快速演示（不需要真实API）
python test_prompt_system.py              # 提示词系统演示
python test_complete_workflow_enhanced.py # 完整工作流演示
```

### Code Quality

```bash
# 代码格式化
black app/ tests/

# 类型检查（如果配置了mypy）
mypy app/
```

### API Documentation

启动服务后访问：
- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc
- Flower监控: http://localhost:5555

## Architecture

### High-Level Structure

```
FastAPI API服务 → Redis任务队列 → Celery Workers
       ↓                             ↓
   存储服务                    视频处理Pipeline
   (本地+OSS)                   ↓
                          1. 视频分析（DashScope AI）
                          2. 语音识别（Paraformer）
                          3. LLM推理（两阶段）
                          4. 视频剪辑（MoviePy 2.x）
```

### Core Components

**三层架构**:
- **API层** (`app/api/v1/`): FastAPI路由，处理HTTP请求
- **Service层** (`app/services/`): 业务逻辑和编排
- **Model层** (`app/models/`): 数据模型和验证（Pydantic）

**异步处理**:
- **Celery Workers** (`app/workers/`): 长时任务的后台处理
- **批处理编排** (`batch_processing_tasks.py`): 完整视频处理Pipeline

**AI集成**:
- **DashScope**: 视觉分析（qwen-vl-plus）和文本生成（qwen-plus）
- **Paraformer**: 语音识别（使用DashScope API）
- **两阶段推理**: Pass 1生成主题 → Pass 2生成剪辑决策

### Key Services

1. **VideoEditingService** (`video_editing.py`):
   - 使用MoviePy 2.x API（`subclipped`, `with_effects`）
   - 实现专业级转场效果（淡入淡出）
   - 视频拼接和音视同步

2. **VideoProductionOrchestrator** (`video_production_orchestrator.py`):
   - 编排完整的视频生产流程
   - TTS语音生成 → 音视频合成
   - 质量评分系统（5维度评估）

3. **BatchProcessingTasks** (`batch_processing_tasks.py`):
   - Pipeline编排：准备 → 分析 → 剪辑决策 → 执行
   - 任务隔离：分析队列和剪辑队列分离
   - 错误处理和重试机制

### Complete Video Production Workflow (NEW - 完整视频生产流程)

**最新实现的核心功能**：将多视频分析、剪辑和视频生产完全整合为一体化工作流。

**工作流阶段**:
1. **视频准备** (并行): 验证、下载、压缩
2. **AI分析** (并行): DashScope VL模型分析每个视频
3. **剪辑计划生成**: LLM基于分析结果生成剪辑决策
4. **剪辑执行**: 提取片段、应用转场、拼接视频
5. **完整生产** (NEW):
   - 脚本生成：基于视频内容生成口播文案
   - TTS合成：并行生成各段语音
   - 音视频合成：混合TTS、背景音乐、视频
   - 质量评分：5维度评估最终质量

**触发条件**:
```python
# 在配置中设置任一选项即启用完整流程
config = {
    "add_narration": True,  # 添加口播旁白
    # 或
    "background_music_path": "/path/to/music.mp3"  # 添加背景音乐
}
```

**关键任务**:
- `produce_final_video_with_narration_task` (`batch_processing_tasks.py:757-899`):
  - 接收剪辑后的视频和分析结果
  - 调用 `VideoProductionOrchestrator.produce_video()`
  - 生成完整的带口播视频

**数据流转**:
```
analyze_video_task → analysis_results
        ↓
generate_clip_plan_task (保存analysis_results)
        ↓
execute_clip_plan_task (传递video_paths + analysis_results)
        ↓
produce_final_video_with_narration_task (生成脚本+TTS+合成)
        ↓
最终视频 + 脚本 + 质量评分
```

**使用场景**:
- 📹 **自媒体创作**: 多素材一键成片
- 📚 **教育视频**: 自动生成讲解视频
- 📰 **新闻快讯**: 素材自动生成解说
- 🎬 **Vlog制作**: 旅行素材自动故事化

**API示例**:
```bash
# 完整视频生产请求
POST /api/v1/batch/process
{
  "video_paths": ["video1.mp4", "video2.mp4"],
  "config": {
    "add_narration": true,
    "narration_voice": "longxiaochun",
    "background_music_path": "music.mp3",
    "background_music_volume": 0.2,
    "target_duration": 60
  }
}

# 返回: 完整视频 + 脚本 + 质量评分
```

**质量评分系统** (5维度):
- **narrative_coherence** (叙事连贯性): 脚本与视频内容匹配度
- **audio_video_sync** (音画同步): TTS与视频时间轴对齐
- **content_coverage** (内容覆盖): 视频内容完整性
- **production_quality** (制作质量): 音频混合、转场效果质量
- **engagement_potential** (吸引力): 整体吸引力评估

**演示脚本**: `examples/complete_video_production_demo.py`
- 5个实际使用场景演示
- 基础 vs 完整流程对比
- 完整的错误处理和进度显示

**详细文档**: 参见 `docs/VIDEO_PROCESSING_PIPELINE.md` 的"流程 2.5"章节

### Prompt System (重要特性)

**新型提示词管理系统** (`app/prompts/`):
- **元数据管理**: 版本控制、性能追踪、参数验证
- **注册表系统**: `@register`装饰器自动注册，单例模式管理
- **病毒传播技术**: 10种实测钩子（成功率0.83-0.92）
- **智能推荐**: 根据视频风格自动推荐最佳钩子

**使用方式**:
```python
from app.prompts import initialize_prompts, get_prompt
from app.prompts.viral import ViralHooks, VideoStyle

initialize_prompts()  # 系统启动时调用一次
prompt = get_prompt("clip_decision.enhanced")
hook = ViralHooks.recommend_hook(VideoStyle.TECH)
formatted = prompt.format_prompt(theme="主题", video_analyses=[...])
```

### Critical Implementation Details

**MoviePy 2.x 必须使用新API**:
- ✅ 使用 `clip.subclipped(start, end)` 而不是 `clip.subclip()`
- ✅ 使用 `clip.with_effects([effect])` 而不是直接函数调用
- ✅ 使用 `vfx` 模块：`from moviepy import vfx`

**JSON解析策略** (`utils/json_parser.py`):
1. Markdown代码块提取
2. 括号匹配提取
3. 自动修复常见错误（注释、单引号、尾随逗号）
4. Pydantic验证
5. 详细错误日志

**关键时刻提取** (`batch_processing_tasks.py::extract_key_moments`):
- 支持多种时间格式：HH:MM:SS、MM:SS、秒数
- 基于关键词的置信度评分
- 5秒窗口去重
- 自动描述提取

**质量评分算法** (`batch_processing_tasks.py::calculate_clip_plan_quality`):
- 视频覆盖率（30%）：源视频使用率
- 时长符合度（25%）：与目标时长匹配
- 片段多样性（20%）：片段数量和分布
- 优先级质量（15%）：高优先级片段比例
- AI分析质量（10%）：推理完整性

## Configuration

### Environment Variables

核心必需配置（`.env`文件）:
```bash
# 必填：阿里云DashScope API密钥
DASHSCOPE_API_KEY=sk-xxxxxxxxxx

# 存储模式：local（本地）、oss（云端）、hybrid（混合，推荐）
STORAGE_BACKEND=hybrid

# 任务存储：true=Redis持久化，false=内存（重启丢失）
USE_REDIS_FOR_TASKS=true

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

### Storage Modes

- **local**: 仅本地存储（开发环境）
- **oss**: 仅OSS云存储（需配置阿里云凭证）
- **hybrid**: 本地缓存 + OSS持久化（生产推荐）

## Code Patterns and Conventions

### Service Layer Patterns

1. **服务类使用单例模式**:
```python
# 在模块末尾导出单例
video_editing_service = VideoEditingService()
```

2. **异步操作使用async/await**:
```python
async def analyze_video(video_path: str) -> VideoAnalysis:
    # 使用httpx进行异步HTTP调用
    async with httpx.AsyncClient() as client:
        response = await client.post(...)
```

3. **错误处理要详细记录**:
```python
try:
    result = await process_video(video_id)
except VideoProcessingError as e:
    logger.error("视频处理失败", video_id=video_id, error=str(e))
    raise
```

### Celery Task Patterns

1. **任务装饰器配置**:
```python
@celery_app.task(
    bind=True,
    name="app.workers.analyze_video",
    max_retries=3,
    default_retry_delay=60
)
def analyze_video_task(self, video_id: str):
    # 任务实现
```

2. **任务链式调用**:
```python
from celery import chain
result = chain(
    prepare_video_task.s(video_id),
    analyze_video_task.s(),
    generate_clip_plan_task.s()
).apply_async()
```

3. **任务隔离原则**:
- 分析任务使用 `analyzer` 队列
- 剪辑任务使用 `clipper` 队列
- 避免队列阻塞

### Model Validation

所有数据模型使用Pydantic v2:
```python
from pydantic import BaseModel, Field, field_validator

class ClipSegment(BaseModel):
    video_id: str = Field(..., description="源视频ID")
    start_time: float = Field(..., ge=0, description="开始时间（秒）")

    @field_validator("start_time")
    def validate_time(cls, v):
        if v < 0:
            raise ValueError("时间不能为负数")
        return v
```

## Working with Video Processing

### Adding New Video Effects

MoviePy 2.x的effects必须通过`with_effects`方法：
```python
from moviepy import vfx

# ✅ 正确方式
clip_with_effect = clip.with_effects([
    vfx.FadeIn(duration=0.5),
    vfx.FadeOut(duration=0.5)
])

# ❌ 错误方式（旧API）
# clip = clip.fadein(0.5)  # 不要使用
```

### Adding New AI Prompts

1. 在 `app/prompts/` 创建新提示词类
2. 继承 `BasePrompt` 或其子类
3. 使用 `@PromptRegistry.register` 装饰器
4. 在 `app/prompts/__init__.py` 中导入
5. 系统自动发现和注册

```python
from app.prompts.base import VisionPrompt
from app.prompts.registry import PromptRegistry
from app.prompts.metadata import PromptMetadata

@PromptRegistry.register
class MyNewPrompt(VisionPrompt):
    def __init__(self):
        metadata = PromptMetadata(
            name="my_new_prompt",
            version="1.0.0",
            category=PromptCategory.VISION_ANALYSIS
        )
        super().__init__(metadata)
```

## Common Workflows

### Adding a New Video Analysis Feature

1. 在 `app/models/` 定义数据模型
2. 在 `app/services/video_analyzer.py` 添加分析逻辑
3. 在 `app/workers/batch_processing_tasks.py` 集成到Pipeline
4. 在 `app/api/v1/` 添加API端点（如需要）
5. 添加测试到 `tests/`

### Debugging Celery Tasks

```bash
# 查看Celery Worker日志
docker-compose logs -f worker-analyzer

# 检查Redis连接
redis-cli ping

# 查看任务队列状态
celery -A app.workers.celery_app inspect active

# 清空队列（开发用）
celery -A app.workers.celery_app purge
```

### Working with Storage

```python
from app.adapters.storage_adapter import storage_adapter

# 保存文件（自动根据STORAGE_BACKEND配置）
storage_path = await storage_adapter.save_file(
    data=video_bytes,
    path="videos/output.mp4",
    content_type="video/mp4"
)

# 获取文件URL
url = storage_adapter.get_url("videos/output.mp4")
```

## Important Notes

- **MoviePy 2.x专用**: 项目完全基于MoviePy 2.x，不兼容1.x API
- **异步优先**: 所有I/O操作使用async/await
- **健壮性**: JSON解析、时间戳提取都有多重回退策略
- **中文日志**: 日志和错误信息使用中文，便于团队协作
- **提示词系统**: 使用统一的提示词管理系统，不要硬编码提示词
- **质量评分**: 所有剪辑计划必须经过5维度质量评分
- **任务持久化**: 生产环境必须设置 `USE_REDIS_FOR_TASKS=true`
