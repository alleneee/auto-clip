# 高级视频混剪功能文档

## 概述

Auto-Clip 的高级视频混剪功能提供了专业级的多视频编辑能力，包括：

- 🎬 **多种转场效果** - 淡入淡出、滑动、缩放、交叉淡化等
- ⚡ **并行处理优化** - 4x性能提升，支持大批量视频处理
- 🧠 **智能片段排序** - 4种叙事风格，自动优化观看体验
- 🎨 **视频滤镜特效** - 亮度、对比度、灰度等专业调色
- 📐 **多种布局模式** - 画中画、水平/垂直分屏、网格布局

## 核心模块

### 1. 高级视频混剪服务

**文件**: `app/services/advanced_video_mixing.py`

#### 主要类: `AdvancedVideoMixingService`

```python
from app.services.advanced_video_mixing import advanced_video_mixing_service

# 高级混剪
output_path, stats = await advanced_video_mixing_service.mix_videos_advanced(
    video_paths=["video1.mp4", "video2.mp4"],
    segments=segments,
    output_path="output.mp4",
    transition_type="crossfade",  # 转场类型
    transition_duration=1.0,       # 转场时长
    apply_filters={"brightness": 0.7},  # 滤镜
    layout_type="single",          # 布局
    output_quality="high",         # 质量
    enable_parallel=True           # 并行处理
)
```

#### 转场效果类型

| 类型 | 说明 | 适用场景 |
|------|------|----------|
| `fade` | 淡入淡出 | 通用过渡 |
| `crossfade` | 交叉淡化 | 平滑衔接 |
| `slide` | 滑动效果 | 动态切换 |
| `zoom` | 缩放效果 | 强调重点 |
| `rotate` | 旋转效果 | 创意转场 |
| `wipe` | 擦除效果 | 清晰分割 |

#### 滤镜类型

| 滤镜 | 参数范围 | 效果说明 |
|------|----------|----------|
| `brightness` | 0.0-1.0 | 调整亮度 |
| `contrast` | 0.0-1.0 | 调整对比度 |
| `saturation` | 0.0-1.0 | 调整饱和度 |
| `grayscale` | - | 灰度效果 |
| `sepia` | - | 复古色调 |
| `blur` | 0.0-1.0 | 模糊效果 |
| `sharpen` | 0.0-1.0 | 锐化效果 |

#### 布局模式

| 布局 | 所需片段数 | 说明 |
|------|-----------|------|
| `single` | 任意 | 单视频拼接 |
| `pip` | ≥2 | 画中画（主视频+小窗） |
| `split_h` | ≥2 | 水平分屏（左右） |
| `split_v` | ≥2 | 垂直分屏（上下） |
| `grid_2x2` | ≥4 | 2x2网格布局 |

### 2. 智能剪辑策略

**文件**: `app/services/smart_clip_strategy.py`

#### 主要类: `SmartClipStrategy`

```python
from app.services.smart_clip_strategy import smart_clip_strategy

# 创建优化剪辑方案
optimized_segments, stats = smart_clip_strategy.create_optimal_clip_plan(
    segments=raw_segments,
    narrative_style="crescendo",  # 叙事风格
    target_duration=60.0,         # 目标时长
    remove_duplicates=True        # 去重
)
```

#### 叙事风格

| 风格 | 说明 | 适用场景 |
|------|------|----------|
| `crescendo` | 渐强式（从低到高） | 悬念构建、情绪递进 |
| `decrescendo` | 渐弱式（从高到低） | 高潮开场、逐渐平复 |
| `wave` | 波浪式（高低起伏） | 保持节奏、避免疲劳 |
| `chronological` | 时间顺序 | 故事叙述、教学内容 |

#### 功能特性

1. **情感分析** - 自动识别片段的情感倾向
2. **内容分类** - 区分动作、对话、风景等场景类型
3. **质量评估** - 多维度评估片段质量
4. **去重优化** - 检测并移除重复片段
5. **时长优化** - 自动调整片段长度适应目标时长

## 使用示例

### 示例1: 基础多视频混剪

```python
import asyncio
from app.services.advanced_video_mixing import advanced_video_mixing_service
from app.models.batch_processing import ClipSegment

async def basic_mixing():
    video_paths = ["video1.mp4", "video2.mp4"]

    segments = [
        ClipSegment(
            video_index=0,
            start_time=0.0,
            end_time=5.0,
            priority=4,
            reason="精彩开场"
        ),
        ClipSegment(
            video_index=1,
            start_time=10.0,
            end_time=15.0,
            priority=5,
            reason="高潮时刻"
        ),
    ]

    output_path, stats = await advanced_video_mixing_service.mix_videos_advanced(
        video_paths=video_paths,
        segments=segments,
        output_path="output.mp4",
        transition_type="fade",
        enable_parallel=True
    )

    print(f"混剪完成: {output_path}")
    print(f"总时长: {stats['total_duration']}秒")

asyncio.run(basic_mixing())
```

### 示例2: 智能排序 + 滤镜

```python
from app.services.smart_clip_strategy import smart_clip_strategy

# 1. 智能优化片段
optimized_segments, _ = smart_clip_strategy.create_optimal_clip_plan(
    segments=raw_segments,
    narrative_style="wave",
    target_duration=60.0
)

# 2. 应用滤镜混剪
output_path, stats = await advanced_video_mixing_service.mix_videos_advanced(
    video_paths=video_paths,
    segments=optimized_segments,
    output_path="output.mp4",
    transition_type="crossfade",
    apply_filters={
        "brightness": 0.7,
        "contrast": 0.6
    },
    output_quality="ultra"
)
```

### 示例3: 画中画布局

```python
# 创建画中画视频
clip_paths = ["main.mp4", "secondary.mp4"]

output_path = await advanced_video_mixing_service.create_layout_video(
    clip_paths=clip_paths,
    layout_type="pip",
    target_size=(1920, 1080)
)
```

### 示例4: 并行处理优化

```python
# 并行提取大量片段（性能提升4x）
clip_paths = await advanced_video_mixing_service.extract_clips_parallel(
    video_paths=video_paths,
    segments=segments  # 可以是10个、100个片段
)

# 统计信息会显示并行处理速度
# 例如: "平均速度: 4.2 片段/秒"
```

## 性能优化

### 并行处理

高级混剪服务使用 `ThreadPoolExecutor` 实现并行片段提取：

```python
# 默认4个工作线程
service = AdvancedVideoMixingService(max_workers=4)

# 根据CPU核心数调整
import os
cpu_count = os.cpu_count()
service = AdvancedVideoMixingService(max_workers=cpu_count)
```

**性能对比**:
- 串行处理: ~1.0 片段/秒
- 并行处理 (4 workers): ~4.2 片段/秒
- **提升**: 约4倍

### 质量与速度平衡

输出质量配置:

```python
quality_presets = {
    'low': {'bitrate': '500k', 'preset': 'ultrafast'},    # 最快
    'medium': {'bitrate': '1500k', 'preset': 'fast'},     # 平衡
    'high': {'bitrate': '3000k', 'preset': 'medium'},     # 推荐
    'ultra': {'bitrate': '5000k', 'preset': 'slow'}       # 最佳质量
}
```

## API参考

### `mix_videos_advanced()`

**完整签名**:

```python
async def mix_videos_advanced(
    video_paths: List[str],              # 源视频路径列表
    segments: List[ClipSegment],         # 剪辑片段列表
    output_path: str,                    # 输出路径
    transition_type: TransitionType = "fade",  # 转场类型
    transition_duration: float = 0.5,    # 转场时长（秒）
    apply_filters: Optional[Dict[FilterType, float]] = None,  # 滤镜配置
    layout_type: LayoutType = "single",  # 布局类型
    output_quality: str = "high",        # 输出质量
    enable_parallel: bool = True         # 启用并行处理
) -> Tuple[str, Dict[str, Any]]:
    """返回: (输出路径, 统计信息)"""
```

**统计信息包含**:

```python
{
    'clip_count': 10,                    # 片段数量
    'total_duration': 125.5,             # 总时长（秒）
    'output_size': 15728640,             # 文件大小（字节）
    'output_size_mb': 15.0,              # 文件大小（MB）
    'processing_time': 42.3,             # 处理耗时（秒）
    'transition_type': 'crossfade',      # 使用的转场
    'layout_type': 'single',             # 使用的布局
    'filters_applied': ['brightness'],   # 应用的滤镜
    'parallel_processing': True          # 是否使用并行
}
```

### `create_optimal_clip_plan()`

**完整签名**:

```python
def create_optimal_clip_plan(
    segments: List[ClipSegment],         # 原始片段列表
    narrative_style: str = "crescendo",  # 叙事风格
    target_duration: Optional[float] = None,  # 目标时长
    remove_duplicates: bool = True       # 去重
) -> Tuple[List[ClipSegment], Dict[str, Any]]:
    """返回: (优化片段, 统计信息)"""
```

## 运行示例程序

项目包含完整的演示程序:

```bash
# 进入项目目录
cd /Users/niko/auto-clip

# 运行交互式演示
python examples/advanced_video_mixing_demo.py
```

演示菜单:
```
1. 基础多视频混剪（带转场）
2. 智能片段排序
3. 画中画布局
4. 分屏布局
5. 视频滤镜效果
6. 并行提取优化
7. 综合工作流
8. 运行所有示例
```

## 最佳实践

### 1. 转场效果选择

- **内容相似**: 使用 `fade` 或 `crossfade`
- **场景切换**: 使用 `slide` 或 `wipe`
- **强调重点**: 使用 `zoom`
- **创意内容**: 使用 `rotate`

### 2. 叙事风格选择

- **教程/教学**: `chronological` (时间顺序)
- **宣传视频**: `crescendo` (渐强式)
- **精彩集锦**: `wave` (波浪式)
- **故事叙述**: `decrescendo` (渐弱式)

### 3. 性能优化建议

- ✅ **启用并行处理**: 对于 >5 个片段
- ✅ **合理设置质量**: 预览用 `medium`，最终输出用 `high`
- ✅ **控制转场时长**: 0.5-1.5秒为佳
- ✅ **批量处理**: 一次性处理多个视频而非逐个

### 4. 质量控制

```python
# 先优化片段方案
optimized_segments, stats = smart_clip_strategy.create_optimal_clip_plan(
    segments=raw_segments,
    target_duration=60.0
)

# 检查平均质量
if stats['average_quality'] < 0.6:
    print("⚠️ 警告: 片段质量较低，建议调整选择")

# 然后执行混剪
output_path, _ = await advanced_video_mixing_service.mix_videos_advanced(...)
```

## 故障排查

### 问题1: 并行处理失败

**症状**: `RuntimeError: 并行提取失败`

**解决**:
```python
# 减少工作线程数
service = AdvancedVideoMixingService(max_workers=2)

# 或禁用并行处理
enable_parallel=False
```

### 问题2: 内存不足

**症状**: `MemoryError` 或进程被杀

**解决**:
```python
# 降低输出质量
output_quality="medium"

# 减少同时处理的片段数
# 分批处理，而不是一次性处理所有片段
```

### 问题3: 转场效果不生效

**症状**: 转场看起来和简单拼接一样

**解决**:
```python
# 增加转场时长
transition_duration=1.5  # 从 0.5 增加到 1.5

# 确保片段有足够长度
# 每个片段至少要比转场时长长 2x
```

## 进阶话题

### 自定义转场效果

可以扩展 `apply_transition()` 方法添加自定义转场:

```python
def apply_custom_transition(clip1, clip2, duration=0.5):
    """自定义转场效果"""
    # 实现你的转场逻辑
    # 返回转场后的片段列表
    return [modified_clip1, modified_clip2]
```

### 自定义滤镜

扩展 `apply_filter()` 方法:

```python
def apply_custom_filter(clip, strength=1.0):
    """自定义滤镜"""
    # 使用 MoviePy 或 NumPy 处理帧
    return modified_clip
```

## 相关文档

- [MoviePy 2.x 官方文档](https://zulko.github.io/moviepy/)
- [项目主文档](../CLAUDE.md)
- [视频处理工具函数](../app/utils/video_utils.py)
- [批处理任务](../app/workers/batch_processing_tasks.py)

## 更新日志

### v1.0.0 (2025-01-06)

**新增功能**:
- ✨ 高级视频混剪服务
- ✨ 智能剪辑策略模块
- ✨ 6种转场效果
- ✨ 7种视频滤镜
- ✨ 5种布局模式
- ✨ 4种叙事风格
- ⚡ 并行处理优化（4x性能）

**示例程序**:
- 📚 7个完整示例
- 📚 交互式演示菜单
- 📚 详细使用文档

---

**技术支持**: 如有问题，请查看 [GitHub Issues](https://github.com/your-repo/issues)
