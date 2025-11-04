# 多视频批处理与智能裁剪系统设计

> **设计目标**: 支持多视频批量输入，通过压缩版本降低VL模型Token成本，使用原始视频进行高质量裁剪拼接

## 📋 需求概述

### 核心需求
1. **多视频批处理**: 支持本地文件、OSS地址、外部URL混合输入
2. **成本优化**: 通过视频压缩降低qwen-vl-plus的Token消耗
3. **两阶段AI分析**:
   - 阶段1: VL模型并行分析每个压缩视频
   - 阶段2: 文本模型汇总生成跨视频裁剪方案
4. **高质量输出**: 从原始视频切分拼接，保证成品质量
5. **时长限制**: 单个视频不超过10分钟

### 业务价值
- **Token成本节省**: VL模型分析成本降低50-80%
- **灵活输入**: 支持多种视频来源混合处理
- **智能裁剪**: AI跨视频理解生成最优裁剪方案
- **质量保证**: 最终成品使用原始高清视频

---

## 🏗️ 系统架构

### 完整工作流

```
┌─────────────────────────────────────────────────────────────────┐
│              1. 多视频输入（混合来源）                          │
│   video_sources = [                                             │
│     {"type": "local", "path": "/path/to/video1.mp4"},           │
│     {"type": "oss", "url": "https://oss.../video2.mp4"},        │
│     {"type": "url", "url": "https://cdn.../video3.mp4"}         │
│   ]                                                              │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│         2. 并行准备：下载 + 验证（所有视频）                    │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│   │ video1.mp4  │  │ video2.mp4  │  │ video3.mp4  │            │
│   │ (本地读取)  │  │ (OSS下载)   │  │ (URL下载)   │            │
│   │ 验证≤10min  │  │ 验证≤10min  │  │ 验证≤10min  │            │
│   └─────────────┘  └─────────────┘  └─────────────┘            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│           3. 并行压缩（所有视频，成本优化）                     │
│   ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐   │
│   │ compressed_1    │  │ compressed_2    │  │ compressed_3 │   │
│   │ 480p/720p/1080p │  │ 降低帧率/码率   │  │ FFmpeg压缩   │   │
│   └─────────────────┘  └─────────────────┘  └──────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│        4. 并行上传到OSS临时区（生成签名URL）                    │
│   ┌─────────────────────────────────────────────────────┐       │
│   │ temp-compressed/{task_id}/                          │       │
│   │   ├─ compressed_0_20241104.mp4 → OSS_URL_1          │       │
│   │   ├─ compressed_1_20241104.mp4 → OSS_URL_2          │       │
│   │   └─ compressed_2_20241104.mp4 → OSS_URL_3          │       │
│   │ 生命周期：1-24小时自动删除                           │       │
│   └─────────────────────────────────────────────────────┘       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│    5. 阶段1 - VL模型并行分析（使用压缩版OSS URL）               │
│   ┌──────────────────────────────────────────────────┐          │
│   │ for url in [OSS_URL_1, OSS_URL_2, OSS_URL_3]:   │          │
│   │   result = qwen-vl-plus.analyze(url)             │          │
│   │                                                   │          │
│   │ 分析结果列表：                                     │          │
│   │ [                                                 │          │
│   │   {                                               │          │
│   │     "video_index": 0,                             │          │
│   │     "content": "运动场景，足球比赛片段...",       │          │
│   │     "duration": 580,                              │          │
│   │     "highlights": ["精彩进球", "激烈对抗"]        │          │
│   │   },                                              │          │
│   │   {                                               │          │
│   │     "video_index": 1,                             │          │
│   │     "content": "采访内容，教练战术分析...",       │          │
│   │     "duration": 420,                              │          │
│   │     "highlights": ["战术讲解", "赛后感想"]        │          │
│   │   },                                              │          │
│   │   {                                               │          │
│   │     "video_index": 2,                             │          │
│   │     "content": "球场全景，观众欢呼...",           │          │
│   │     "duration": 300,                              │          │
│   │     "highlights": ["气氛镜头", "庆祝瞬间"]        │          │
│   │   }                                               │          │
│   │ ]                                                 │          │
│   └──────────────────────────────────────────────────┘          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│    6. 阶段2 - 文本模型生成跨视频裁剪方案                        │
│   ┌──────────────────────────────────────────────────┐          │
│   │ qwen-plus(                                        │          │
│   │   prompt="基于以下视频分析结果，生成精彩集锦裁剪方案", │      │
│   │   analysis_results=[结果1, 结果2, 结果3]          │          │
│   │ )                                                 │          │
│   │                                                   │          │
│   │ 返回裁剪决策：                                     │          │
│   │ {                                                 │          │
│   │   "theme": "足球比赛精彩瞬间",                     │          │
│   │   "clips": [                                      │          │
│   │     {                                             │          │
│   │       "video_index": 0,  // 对应video1           │          │
│   │       "start": 125.5,                             │          │
│   │       "end": 145.2,                               │          │
│   │       "reason": "精彩进球瞬间"                     │          │
│   │     },                                            │          │
│   │     {                                             │          │
│   │       "video_index": 2,  // 对应video3           │          │
│   │       "start": 30.0,                              │          │
│   │       "end": 50.5,                                │          │
│   │       "reason": "观众激情反应"                     │          │
│   │     },                                            │          │
│   │     {                                             │          │
│   │       "video_index": 0,  // 再次使用video1        │          │
│   │       "start": 200.0,                             │          │
│   │       "end": 230.5,                               │          │
│   │       "reason": "激烈对抗场面"                     │          │
│   │     },                                            │          │
│   │     {                                             │          │
│   │       "video_index": 1,  // 对应video2           │          │
│   │       "start": 80.0,                              │          │
│   │       "end": 120.0,                               │          │
│   │       "reason": "教练战术讲解"                     │          │
│   │     }                                             │          │
│   │   ]                                               │          │
│   │ }                                                 │          │
│   └──────────────────────────────────────────────────┘          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│    7. MoviePy执行：从原始视频切分 + 拼接                        │
│   ┌──────────────────────────────────────────────────┐          │
│   │ # 从原始高清视频切分片段                           │          │
│   │ clip_1 = original_video_0.subclip(125.5, 145.2)   │          │
│   │ clip_2 = original_video_2.subclip(30.0, 50.5)     │          │
│   │ clip_3 = original_video_0.subclip(200.0, 230.5)   │          │
│   │ clip_4 = original_video_1.subclip(80.0, 120.0)    │          │
│   │                                                   │          │
│   │ # 按顺序拼接                                       │          │
│   │ final = concatenate_videoclips([                  │          │
│   │   clip_1, clip_2, clip_3, clip_4                  │          │
│   │ ])                                                │          │
│   │                                                   │          │
│   │ # 可选：重新编码或保持原始质量                     │          │
│   │ final.write_videofile(                            │          │
│   │   "final.mp4",                                    │          │
│   │   codec="libx264",                                │          │
│   │   bitrate="5000k"  // 根据配置                    │          │
│   │ )                                                 │          │
│   └──────────────────────────────────────────────────┘          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│    8. 上传成品到OSS + 清理临时文件                               │
│   ├─ 上传最终视频到 processed/{task_id}/final.mp4               │
│   ├─ 生成公开/私有URL                                            │
│   ├─ 删除本地原始视频                                            │
│   ├─ 删除本地压缩视频                                            │
│   ├─ 删除OSS临时压缩文件                                         │
│   └─ 发送Webhook回调                                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ 配置系统设计

### 1. 压缩策略配置（与之前相同）

```python
# app/config.py 扩展

class CompressionProfile(BaseModel):
    """压缩配置档案"""
    name: str
    max_resolution: str       # "480p", "720p", "1080p"
    target_fps: int           # 5, 15, 24, 30
    video_bitrate: str        # "500k", "1500k", "3000k"
    audio_bitrate: str        # "64k", "128k", "192k"
    audio_sample_rate: int    # 22050, 44100
    video_codec: str = "libx264"
    preset: str               # "ultrafast", "fast", "medium"
    crf: int                  # 18-28 (质量参数)

# 预设策略
COMPRESSION_PROFILES = {
    "aggressive": CompressionProfile(
        name="aggressive",
        max_resolution="480p",
        target_fps=10,
        video_bitrate="500k",
        audio_bitrate="64k",
        audio_sample_rate=22050,
        preset="ultrafast",
        crf=28
    ),
    "balanced": CompressionProfile(
        name="balanced",
        max_resolution="720p",
        target_fps=15,
        video_bitrate="1500k",
        audio_bitrate="128k",
        audio_sample_rate=44100,
        preset="fast",
        crf=23
    ),
    "conservative": CompressionProfile(
        name="conservative",
        max_resolution="1080p",
        target_fps=24,
        video_bitrate="3000k",
        audio_bitrate="192k",
        audio_sample_rate=44100,
        preset="medium",
        crf=20
    ),
}

# 动态策略：根据视频时长自动选择
DYNAMIC_COMPRESSION_RULES = {
    "0-180": "conservative",    # 0-3分钟
    "180-420": "balanced",      # 3-7分钟
    "420-600": "aggressive",    # 7-10分钟
}
```

### 2. 视频来源配置

```python
# app/models/video_source.py

from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional

class VideoSourceType(str, Enum):
    """视频来源类型"""
    LOCAL = "local"      # 本地文件路径
    OSS = "oss"          # OSS URL
    URL = "url"          # 外部URL

class VideoSource(BaseModel):
    """视频来源定义"""
    type: VideoSourceType

    # local类型参数
    path: Optional[str] = Field(
        None,
        description="本地文件绝对路径"
    )

    # oss/url类型参数
    url: Optional[str] = Field(
        None,
        description="OSS URL或外部URL"
    )

    # 可选：自定义压缩配置（覆盖全局配置）
    compression_profile: Optional[str] = None

# 使用示例
video_sources = [
    VideoSource(type="local", path="/Users/niko/videos/clip1.mp4"),
    VideoSource(type="oss", url="https://bucket.oss-cn-hangzhou.aliyuncs.com/video2.mp4"),
    VideoSource(type="url", url="https://cdn.example.com/video3.mp4", compression_profile="aggressive")
]
```

---

## 🔌 API接口设计

### 请求模型

```python
# app/models/requests.py

from pydantic import BaseModel, Field
from typing import List, Optional

class BatchVideoProcessRequest(BaseModel):
    """批量视频处理请求"""

    # 视频来源列表
    video_sources: List[VideoSource] = Field(
        ...,
        min_items=1,
        max_items=10,  # 限制最多10个视频
        description="视频来源列表（本地/OSS/URL混合）"
    )

    # 全局压缩配置（可被单个视频配置覆盖）
    compression_profile: str = Field(
        default="balanced",
        description="默认压缩策略：aggressive/balanced/conservative/dynamic"
    )

    # 临时存储配置
    temp_url_expiry: int = Field(
        default=3600,
        ge=600,
        le=86400,
        description="临时URL有效期（秒）"
    )

    # 输出配置
    output_mode: str = Field(
        default="original_quality",
        description="输出模式：original_quality/recompress"
    )
    output_resolution: Optional[str] = Field(
        default="1080p",
        description="重编码分辨率（recompress模式）"
    )
    output_fps: Optional[int] = Field(
        default=30,
        description="重编码帧率（recompress模式）"
    )
    output_bitrate: Optional[str] = Field(
        default="5000k",
        description="重编码码率（recompress模式）"
    )

    # AI分析配置
    enable_vl_analysis: bool = Field(
        default=True,
        description="启用VL模型视觉分析"
    )
    enable_asr: bool = Field(
        default=False,
        description="启用Paraformer语音识别"
    )

    # 回调配置
    webhook_url: Optional[str] = Field(
        None,
        description="完成后回调URL"
    )

    # 业务参数
    custom_prompt: Optional[str] = Field(
        None,
        description="自定义裁剪需求提示词（影响第二阶段AI生成）"
    )
```

### 响应模型

```python
# app/models/responses.py

class BatchVideoProcessResponse(BaseModel):
    """批量视频处理响应"""

    task_id: str
    status: str  # "queued", "processing"

    # 视频列表信息
    videos_info: List[dict] = Field(
        ...,
        description="每个视频的元信息",
        example=[
            {
                "index": 0,
                "source_type": "local",
                "duration": 580.5,
                "resolution": "1920x1080",
                "size_mb": 150.2,
                "compressed_url": "https://oss.../temp-compressed/..."
            },
            {
                "index": 1,
                "source_type": "oss",
                "duration": 420.0,
                "resolution": "1280x720",
                "size_mb": 80.5,
                "compressed_url": "https://oss.../temp-compressed/..."
            }
        ]
    )

    # 压缩统计
    compression_summary: dict = Field(
        ...,
        example={
            "total_original_size_mb": 230.7,
            "total_compressed_size_mb": 78.3,
            "average_compression_ratio": 0.66,
            "estimated_token_savings": "~70%"
        }
    )

    # 预计完成时间
    estimated_completion: str
    created_at: str


class TaskStatusResponse(BaseModel):
    """任务状态响应（扩展）"""

    task_id: str
    status: str
    progress: int  # 0-100
    current_stage: str

    # 各阶段详细状态
    stages: dict = Field(
        default_factory=dict,
        example={
            "preparation": {
                "status": "completed",
                "videos_processed": 3,
                "duration_seconds": 15.2
            },
            "compression": {
                "status": "completed",
                "videos_compressed": 3,
                "total_size_reduction_mb": 152.4,
                "duration_seconds": 45.8
            },
            "vl_analysis": {
                "status": "completed",
                "videos_analyzed": 3,
                "duration_seconds": 120.5
            },
            "clip_generation": {
                "status": "in_progress",
                "clips_generated": 2,
                "total_clips": 4
            }
        }
    )

    # VL分析结果（第一阶段完成后）
    vl_analysis_results: Optional[List[dict]] = Field(
        None,
        example=[
            {
                "video_index": 0,
                "content": "运动场景...",
                "highlights": ["进球", "对抗"]
            }
        ]
    )

    # 裁剪方案（第二阶段完成后）
    clip_decisions: Optional[dict] = Field(
        None,
        example={
            "theme": "足球精彩集锦",
            "clips": [
                {"video_index": 0, "start": 125.5, "end": 145.2},
                {"video_index": 2, "start": 30.0, "end": 50.5}
            ]
        }
    )

    # 成品信息（完成后）
    final_video_url: Optional[str] = None
    final_video_info: Optional[dict] = None

    # 错误信息
    error: Optional[str] = None
    error_details: Optional[List[dict]] = None  # 每个视频的错误

    created_at: str
    updated_at: str
    completed_at: Optional[str] = None


# 任务状态枚举（扩展）
TASK_STATUSES = {
    "queued": "排队中",
    "preparing": "准备视频中",
    "downloading": "下载视频中",
    "compressing": "批量压缩中",
    "uploading_temp": "上传临时文件",
    "vl_analyzing": "VL模型分析中",
    "generating_plan": "生成裁剪方案",
    "clipping": "切分视频中",
    "merging": "拼接片段中",
    "uploading_final": "上传成品",
    "cleanup": "清理临时文件",
    "completed": "已完成",
    "failed": "失败",
    "cancelled": "已取消"
}
```

### API路由

```python
# app/api/v1/videos.py（重新设计）

@router.post("/batch-process", response_model=BatchVideoProcessResponse)
async def batch_process_videos(
    request: BatchVideoProcessRequest,
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    批量视频处理入口

    支持混合输入：
    - local: 本地文件路径
    - oss: OSS URL
    - url: 外部URL

    完整流程：
    1. 并行准备所有视频（下载/读取）
    2. 并行压缩所有视频
    3. 并行上传到临时OSS
    4. VL模型并行分析
    5. 文本模型生成裁剪方案
    6. MoviePy切分拼接
    7. 上传成品并清理
    """

    # 1. 生成任务ID
    task_id = generate_task_id()

    # 2. 验证视频来源数量
    if len(request.video_sources) > 10:
        raise HTTPException(400, "最多支持10个视频同时处理")

    # 3. 快速验证每个视频来源的有效性
    validated_sources = []
    for i, source in enumerate(request.video_sources):
        try:
            # 验证路径/URL可访问性
            await validate_video_source(source)
            validated_sources.append({
                "index": i,
                "source": source
            })
        except Exception as e:
            raise HTTPException(400, f"视频{i}无效: {str(e)}")

    # 4. 创建批处理工作流
    workflow = create_batch_processing_workflow(
        task_id=task_id,
        video_sources=validated_sources,
        compression_profile=request.compression_profile,
        temp_url_expiry=request.temp_url_expiry,
        output_config={
            "mode": request.output_mode,
            "resolution": request.output_resolution,
            "fps": request.output_fps,
            "bitrate": request.output_bitrate
        },
        ai_config={
            "enable_vl": request.enable_vl_analysis,
            "enable_asr": request.enable_asr,
            "custom_prompt": request.custom_prompt
        },
        webhook_url=request.webhook_url
    )

    # 5. 异步执行
    result = workflow.apply_async()

    # 6. 返回任务信息（初步信息）
    return BatchVideoProcessResponse(
        task_id=task_id,
        status="queued",
        videos_info=[],  # 稍后填充
        compression_summary={},
        estimated_completion=estimate_completion_time(len(validated_sources)),
        created_at=datetime.now().isoformat()
    )


@router.get("/tasks/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """查询批处理任务状态（增强版）"""
    task_data = await get_task_from_store(task_id)

    if not task_data:
        raise HTTPException(404, "任务不存在")

    return TaskStatusResponse(**task_data)


@router.get("/tasks/{task_id}/vl-results")
async def get_vl_analysis_results(task_id: str):
    """
    获取VL分析详细结果

    返回每个视频的详细分析内容
    """
    results = await get_vl_results_from_store(task_id)
    return {"task_id": task_id, "results": results}


@router.get("/tasks/{task_id}/clip-plan")
async def get_clip_plan(task_id: str):
    """
    获取裁剪方案详情

    返回AI生成的完整裁剪决策
    """
    plan = await get_clip_plan_from_store(task_id)
    return {"task_id": task_id, "plan": plan}
```

---

## 🔄 Celery任务编排（重新设计）

### 批处理工作流

```python
# app/workers/batch_processing_tasks.py

from celery import chain, group, chord
from app.workers.celery_app import celery_app

def create_batch_processing_workflow(
    task_id: str,
    video_sources: List[dict],
    compression_profile: str,
    temp_url_expiry: int,
    output_config: dict,
    ai_config: dict,
    webhook_url: str = None
):
    """
    创建批量视频处理工作流

    使用Celery的group和chord实现并行处理
    """

    # 步骤1: 并行准备所有视频（下载/验证）
    prepare_tasks = group([
        prepare_single_video.s(
            task_id=task_id,
            video_index=item["index"],
            source=item["source"]
        )
        for item in video_sources
    ])

    # 步骤2: 并行压缩所有视频
    compress_tasks = group([
        compress_single_video.s(
            task_id=task_id,
            video_index=item["index"],
            compression_profile=compression_profile
        )
        for item in video_sources
    ])

    # 步骤3: 并行上传到临时OSS
    upload_temp_tasks = group([
        upload_single_to_temp_oss.s(
            task_id=task_id,
            video_index=item["index"],
            expiry=temp_url_expiry
        )
        for item in video_sources
    ])

    # 步骤4: 并行VL分析（使用chord汇总结果）
    vl_analysis_workflow = chord(
        # 并行分析
        [
            analyze_single_video_with_vl.s(
                task_id=task_id,
                video_index=item["index"]
            )
            for item in video_sources
        ],
        # 汇总回调
        aggregate_vl_results.s(task_id=task_id)
    )

    # 步骤5: 生成裁剪方案（使用汇总结果）
    generate_plan_task = generate_clip_plan.s(
        task_id=task_id,
        custom_prompt=ai_config.get("custom_prompt")
    )

    # 步骤6: 执行裁剪和拼接
    execute_clip_task = execute_clipping_and_merging.s(
        task_id=task_id,
        output_config=output_config
    )

    # 步骤7: 上传成品
    upload_final_task = upload_final_video.s(task_id=task_id)

    # 步骤8: 清理和通知
    cleanup_task = cleanup_and_notify.s(
        task_id=task_id,
        webhook_url=webhook_url
    )

    # 组合完整工作流
    workflow = chain(
        prepare_tasks,
        compress_tasks,
        upload_temp_tasks,
        vl_analysis_workflow,
        generate_plan_task,
        execute_clip_task,
        upload_final_task,
        cleanup_task
    )

    return workflow


# ========== 单个任务定义 ==========

@celery_app.task(bind=True, max_retries=3)
def prepare_single_video(self, task_id: str, video_index: int, source: dict):
    """
    准备单个视频

    - local: 验证文件存在
    - oss/url: 下载到本地
    - 提取元数据
    - 验证时长 ≤ 10分钟

    返回: {
        "index": 0,
        "local_path": "/path/to/video_0.mp4",
        "duration": 580.5,
        "resolution": "1920x1080",
        "size_mb": 150.2
    }
    """
    self.update_state(
        state='PROGRESS',
        meta={'stage': 'preparing', 'video_index': video_index}
    )

    try:
        if source["type"] == "local":
            video_path = source["path"]
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"本地文件不存在: {video_path}")

        elif source["type"] == "oss":
            # 从OSS下载
            video_path = await download_from_oss(
                source["url"],
                f"{task_id}/original_{video_index}.mp4"
            )

        elif source["type"] == "url":
            # 从外部URL下载
            video_path = await download_from_url(
                source["url"],
                f"{task_id}/original_{video_index}.mp4"
            )

        # 提取元数据
        metadata = await extract_video_metadata(video_path)

        # 验证时长
        if metadata["duration"] > 600:
            raise VideoTooLongError(
                f"视频{video_index}时长{metadata['duration']}秒超过10分钟"
            )

        return {
            "index": video_index,
            "local_path": video_path,
            **metadata
        }

    except Exception as e:
        logger.error(f"准备视频{video_index}失败: {e}")
        raise self.retry(exc=e)


@celery_app.task(bind=True, max_retries=2)
def compress_single_video(
    self,
    video_info: dict,
    task_id: str,
    video_index: int,
    compression_profile: str
):
    """
    压缩单个视频

    返回: {
        "index": 0,
        "original_path": "/path/to/original.mp4",
        "compressed_path": "/path/to/compressed.mp4",
        "compression_ratio": 0.65,
        "size_mb": 52.5
    }
    """
    self.update_state(
        state='PROGRESS',
        meta={'stage': 'compressing', 'video_index': video_index}
    )

    # 使用VideoCompressionService
    service = VideoCompressionService()

    # 选择压缩策略
    if compression_profile == "dynamic":
        profile = service.select_profile(
            duration=video_info["duration"],
            mode="dynamic"
        )
    else:
        profile = COMPRESSION_PROFILES[compression_profile]

    # 压缩
    output_path = f"{settings.cache_dir}/{task_id}/compressed_{video_index}.mp4"
    result = await service.compress_video(
        input_path=video_info["local_path"],
        output_path=output_path,
        profile=profile
    )

    return {
        "index": video_index,
        "original_path": video_info["local_path"],
        "compressed_path": result.compressed_path,
        "compression_ratio": result.compression_ratio,
        "size_mb": result.compressed_size_mb
    }


@celery_app.task(bind=True, max_retries=3)
def upload_single_to_temp_oss(
    self,
    compress_result: dict,
    task_id: str,
    video_index: int,
    expiry: int
):
    """
    上传单个压缩视频到临时OSS

    返回: {
        "index": 0,
        "temp_url": "https://...",
        "oss_key": "temp-compressed/...",
        "expires_at": "2024-01-01T12:00:00Z"
    }
    """
    self.update_state(
        state='PROGRESS',
        meta={'stage': 'uploading_temp', 'video_index': video_index}
    )

    service = TempStorageService()

    result = await service.upload_temp_video(
        local_path=compress_result["compressed_path"],
        task_id=task_id,
        video_index=video_index,
        expiry_seconds=expiry
    )

    return {
        "index": video_index,
        "temp_url": result.temp_url,
        "oss_key": result.oss_key,
        "expires_at": result.expires_at.isoformat()
    }


@celery_app.task(bind=True, max_retries=2)
def analyze_single_video_with_vl(
    self,
    upload_result: dict,
    task_id: str,
    video_index: int
):
    """
    使用VL模型分析单个视频（通过临时URL）

    返回: {
        "video_index": 0,
        "content": "运动场景，足球比赛...",
        "duration": 580.5,
        "highlights": ["进球", "对抗"],
        "tags": ["运动", "足球", "比赛"]
    }
    """
    self.update_state(
        state='PROGRESS',
        meta={'stage': 'vl_analyzing', 'video_index': video_index}
    )

    # 调用DashScope qwen-vl-plus
    from app.utils.ai_clients.dashscope_client import DashScopeClient

    client = DashScopeClient()

    analysis_result = await client.analyze_video_vl(
        video_url=upload_result["temp_url"],
        prompt="详细分析视频内容，识别精彩片段和关键场景"
    )

    return {
        "video_index": video_index,
        "content": analysis_result.get("description"),
        "highlights": analysis_result.get("highlights", []),
        "tags": analysis_result.get("tags", []),
        "scenes": analysis_result.get("scenes", [])
    }


@celery_app.task(bind=True)
def aggregate_vl_results(self, analysis_results: List[dict], task_id: str):
    """
    汇总所有VL分析结果

    这是chord的回调任务，接收所有并行任务的结果

    返回: {
        "task_id": "...",
        "total_videos": 3,
        "results": [...]
    }
    """
    self.update_state(
        state='PROGRESS',
        meta={'stage': 'aggregating_results'}
    )

    # 保存到Redis/数据库供后续查询
    await save_vl_results_to_store(task_id, analysis_results)

    return {
        "task_id": task_id,
        "total_videos": len(analysis_results),
        "results": analysis_results
    }


@celery_app.task(bind=True, max_retries=2)
def generate_clip_plan(
    self,
    aggregated_results: dict,
    task_id: str,
    custom_prompt: str = None
):
    """
    使用文本模型生成跨视频裁剪方案

    输入：所有视频的VL分析结果
    输出：裁剪决策

    返回: {
        "theme": "足球精彩集锦",
        "clips": [
            {"video_index": 0, "start": 125.5, "end": 145.2, "reason": "..."},
            ...
        ]
    }
    """
    self.update_state(
        state='PROGRESS',
        meta={'stage': 'generating_plan'}
    )

    from app.utils.ai_clients.dashscope_client import DashScopeClient

    client = DashScopeClient()

    # 构建提示词
    base_prompt = """
    基于以下多个视频的分析结果，生成一个精彩集锦的裁剪方案。

    要求：
    1. 选择最精彩的片段，总时长控制在2-5分钟
    2. 片段之间要有连贯性和叙事逻辑
    3. 可以从同一个视频选择多个片段
    4. 返回JSON格式，包含每个片段的video_index、start、end和reason

    视频分析结果：
    {analysis_results}
    """

    if custom_prompt:
        base_prompt += f"\n\n用户额外需求：{custom_prompt}"

    # 调用qwen-plus生成方案
    clip_plan = await client.generate_clip_plan(
        prompt=base_prompt.format(
            analysis_results=json.dumps(
                aggregated_results["results"],
                ensure_ascii=False,
                indent=2
            )
        )
    )

    # 验证方案的有效性
    validate_clip_plan(clip_plan, aggregated_results["results"])

    # 保存到存储
    await save_clip_plan_to_store(task_id, clip_plan)

    return clip_plan


@celery_app.task(bind=True)
def execute_clipping_and_merging(
    self,
    clip_plan: dict,
    task_id: str,
    output_config: dict
):
    """
    执行视频切分和拼接（MoviePy）

    从原始高清视频按方案切分，然后拼接成最终视频

    返回: {
        "final_path": "/path/to/final.mp4",
        "duration": 180.5,
        "size_mb": 250.3
    }
    """
    self.update_state(
        state='PROGRESS',
        meta={'stage': 'clipping_and_merging'}
    )

    from app.services.video_editing_service import VideoEditingService

    service = VideoEditingService()

    # 获取原始视频路径映射
    original_videos = await get_original_videos_from_store(task_id)

    # 按照clip_plan切分所有片段
    all_clips = []
    for clip_decision in clip_plan["clips"]:
        video_index = clip_decision["video_index"]
        original_path = original_videos[video_index]["local_path"]

        # 切分单个片段
        clip_path = await service.extract_single_clip(
            video_path=original_path,
            start=clip_decision["start"],
            end=clip_decision["end"],
            output_dir=f"{settings.cache_dir}/{task_id}/clips"
        )

        all_clips.append(clip_path)

        # 更新进度
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'clipping',
                'clips_done': len(all_clips),
                'total_clips': len(clip_plan["clips"])
            }
        )

    # 拼接所有片段
    final_path = f"{settings.processed_dir}/{task_id}/final.mp4"

    await service.concatenate_clips(
        clip_paths=all_clips,
        output_path=final_path,
        output_profile=output_config
    )

    # 获取最终视频信息
    final_metadata = await extract_video_metadata(final_path)

    return {
        "final_path": final_path,
        "duration": final_metadata["duration"],
        "size_mb": final_metadata["size_mb"]
    }


@celery_app.task(bind=True, max_retries=3)
def upload_final_video(self, final_info: dict, task_id: str):
    """上传成品到OSS持久区"""
    self.update_state(
        state='PROGRESS',
        meta={'stage': 'uploading_final'}
    )

    # 上传到 processed/ 目录
    oss_key = f"processed/{task_id}/final_{datetime.now().strftime('%Y%m%d%H%M%S')}.mp4"

    # 使用OSS SDK上传
    # ...

    final_url = f"https://{settings.OSS_BUCKET_NAME}.{settings.OSS_ENDPOINT}/{oss_key}"

    return {
        "final_url": final_url,
        "oss_key": oss_key,
        **final_info
    }


@celery_app.task(bind=True)
def cleanup_and_notify(
    self,
    upload_result: dict,
    task_id: str,
    webhook_url: str = None
):
    """清理临时文件并发送通知"""
    self.update_state(
        state='PROGRESS',
        meta={'stage': 'cleanup'}
    )

    # 1. 删除本地原始视频
    original_videos = await get_original_videos_from_store(task_id)
    for video in original_videos:
        if os.path.exists(video["local_path"]):
            os.remove(video["local_path"])

    # 2. 删除本地压缩视频
    compressed_dir = f"{settings.cache_dir}/{task_id}"
    if os.path.exists(compressed_dir):
        shutil.rmtree(compressed_dir)

    # 3. 删除OSS临时文件
    temp_storage = TempStorageService()
    await temp_storage.cleanup_temp_files(task_id)

    # 4. 发送Webhook通知
    if webhook_url:
        await send_webhook_notification(
            url=webhook_url,
            payload={
                "task_id": task_id,
                "status": "completed",
                "final_video_url": upload_result["final_url"],
                "completed_at": datetime.now().isoformat()
            }
        )

    return {
        "task_id": task_id,
        "status": "completed",
        "final_url": upload_result["final_url"]
    }
```

---

## 📊 实施计划

### 阶段1: 核心服务实现（3-4天）
- [ ] 扩展VideoSource模型支持多来源
- [ ] 实现批量视频准备服务（下载/验证）
- [ ] 更新VideoCompressionService支持批量压缩
- [ ] 更新TempStorageService支持批量上传
- [ ] 单元测试

### 阶段2: AI集成（2-3天）
- [ ] 实现VL模型并行分析
- [ ] 实现结果汇总机制
- [ ] 实现文本模型裁剪方案生成
- [ ] 验证方案有效性
- [ ] 集成测试

### 阶段3: MoviePy集成（2-3天）
- [ ] 实现跨视频切分服务
- [ ] 实现片段拼接服务
- [ ] 输出质量配置
- [ ] 性能优化

### 阶段4: Celery编排（2-3天）
- [ ] 实现group并行任务
- [ ] 实现chord汇总机制
- [ ] 错误处理和重试
- [ ] 进度追踪

### 阶段5: API和测试（2天）
- [ ] 实现批处理API
- [ ] 状态查询增强
- [ ] 端到端测试
- [ ] 文档更新

---

## 💰 成本效益分析

### 实际案例估算

**场景**: 处理3个视频生成1个精彩集锦
- 视频1: 5分钟, 1080p, 500MB
- 视频2: 3分钟, 720p, 200MB
- 视频3: 7分钟, 1080p, 800MB

**使用balanced压缩策略**:

| 项目 | 未压缩 | 压缩后 | 节省 |
|------|--------|--------|------|
| 视频1 Token | ¥80 | ¥28 | **65%** |
| 视频2 Token | ¥40 | ¥14 | **65%** |
| 视频3 Token | ¥120 | ¥42 | **65%** |
| **总Token成本** | **¥240** | **¥84** | **65%** |
| OSS临时存储 | ¥15 | ¥2 | **87%** |
| **总成本** | **¥255** | **¥86** | **66%** |

---

## ⚠️ 关键注意事项

### 1. 并发控制
- 最多同时处理10个视频（API限制）
- Celery worker pool配置要支持并发
- 避免OSS并发上传限流

### 2. 内存管理
- MoviePy加载多个视频可能消耗大量内存
- 考虑分批处理或使用流式处理
- 设置合理的worker并发数

### 3. 错误处理
- 单个视频失败不应影响其他视频
- 提供详细的错误信息（哪个视频出错）
- 支持部分成功的结果返回

### 4. 时间控制
- VL分析可能耗时较长（每视频1-3分钟）
- 设置合理的任务超时时间
- 提供准确的进度反馈

---

**设计完成日期**: 2024-11-04
**版本**: v2.0 (批处理架构)
**负责人**: Auto-Clip开发团队
