# MoviePy 2.x 核心方法参考

本文档总结项目中使用的MoviePy 2.x核心API，以及如何将它们封装为Agent工具。

## MoviePy 2.x 核心API

### 1. 视频剪辑提取

```python
from moviepy import VideoFileClip

# 加载视频
clip = VideoFileClip("video.mp4")

# ✅ MoviePy 2.x 新API
clipped = clip.subclipped(start_time, end_time)

# ❌ MoviePy 1.x 旧API（不要使用）
# clipped = clip.subclip(start_time, end_time)
```

### 2. 视频拼接

```python
from moviepy import concatenate_videoclips

clips = [clip1, clip2, clip3]

# 拼接视频
final_clip = concatenate_videoclips(clips, method="compose")

# 写入文件
final_clip.write_videofile("output.mp4")
```

### 3. 添加转场效果

```python
from moviepy import vfx

# ✅ MoviePy 2.x 新API
clip_with_fade = clip.with_effects([
    vfx.FadeIn(0.5),
    vfx.FadeOut(0.5)
])

# ❌ MoviePy 1.x 旧API（不要使用）
# clip = clip.fadein(0.5).fadeout(0.5)
```

### 4. 获取视频信息

```python
# 基本属性
duration = clip.duration  # 时长（秒）
width = clip.w  # 宽度
height = clip.h  # 高度
fps = clip.fps  # 帧率
```

## Agent工具封装

Agno提供两种工具封装方式，根据需求选择：

### 方式1: Toolkit类（适合复杂工具组织）

```python
from app.tools.video_editing_tool import VideoEditingTools
from agno.agent import Agent

# 方式A: 直接调用工具方法
tools = VideoEditingTools(temp_dir="/tmp")
result_json = tools.extract_clip(
    video_path="/path/to/video.mp4",
    start_time=10.0,
    end_time=20.0
)
result = json.loads(result_json)

# 方式B: 附加到Agent
agent = Agent(
    tools=[VideoEditingTools()],  # 整个工具集
    markdown=True
)

# 方式C: 使用include_tools选择性启用
agent = Agent(
    tools=[VideoEditingTools(include_tools=["extract_clip", "concatenate_clips"])],
    markdown=True
)
```

### 方式2: @tool装饰器（更简洁）

```python
from app.tools.video_editing_decorators import (
    extract_video_clip_tool,
    concatenate_video_clips_tool,
    get_video_metadata
)
from agno.agent import Agent

# 直接传入装饰器函数
agent = Agent(
    tools=[extract_video_clip_tool, concatenate_video_clips_tool, get_video_metadata],
    markdown=True
)

# 或直接调用
result_json = extract_video_clip_tool(
    video_path="/path/to/video.mp4",
    start_time=10.0,
    end_time=20.0
)
result = json.loads(result_json)
```

### 两种方式对比

| 特性 | Toolkit类 | @tool装饰器 |
|------|----------|-------------|
| 代码量 | 较多（类+方法） | 较少（函数+装饰器） |
| 工具组织 | ✅ 统一配置（temp_dir等） | ❌ 每个函数独立 |
| 工具过滤 | ✅ include/exclude支持 | ❌ 手动选择函数 |
| Agent集成 | `tools=[MyToolkit()]` | `tools=[func1, func2]` |
| 使用场景 | 多工具集、需要统一配置 | 简单工具、快速开发 |

### VideoEditingTool完整示例

```python
from app.tools.video_editing_tool import VideoEditingTools
import json

tool = VideoEditingTools()

# 1. 提取片段
result_json = tool.extract_clip(
    video_path="/path/to/video.mp4",
    start_time=10.0,
    end_time=20.0
)
result = json.loads(result_json)

# 2. 拼接视频
result_json = tool.concatenate_clips(
    clip_paths=["/tmp/clip1.mp4", "/tmp/clip2.mp4"],
    output_path="/output/final.mp4",
    add_transitions=True
)
result = json.loads(result_json)

# 3. 获取信息
info_json = tool.get_video_info_tool(video_path="/path/to/video.mp4")
info = json.loads(info_json)

# 4. 执行完整方案
result_json = tool.execute_clip_plan(
    video_paths=["/videos/video1.mp4"],
    segments=[
        {
            "video_id": "video1",
            "start_time": 10.0,
            "end_time": 20.0,
            "role": "opening"
        }
    ],
    output_path="/output/final.mp4"
)
result = json.loads(result_json)
```

### VideoExecutorAgent

高级Agent，执行AgnoClipTeam生成的剪辑方案：

```python
from app.agents.video_executor import VideoExecutorAgent
from app.agents.clip_team import AgnoClipTeam

# 1. 生成AI剪辑方案
team = AgnoClipTeam(...)
result = team.run(video_paths=[...], config={...})

# 2. 执行方案生成视频
executor = VideoExecutorAgent()
exec_result = executor.execute_from_video_paths(
    technical_plan=result.technical_plan,
    video_paths=video_paths,
    output_path="/output/final.mp4"
)
```

## 完整端到端流程

```bash
# 运行端到端测试
python test_end_to_end_video.py
```

流程：
1. **AgnoClipTeam** - AI分析视频，生成剪辑方案
2. **VideoExecutorAgent** - 执行方案，生成实际视频文件
3. **输出** - 最终的剪辑视频（带转场效果）

## MoviePy 2.x 注意事项

### ✅ 正确做法

```python
# 使用 subclipped 而不是 subclip
clip = clip.subclipped(10, 20)

# 使用 with_effects 添加效果
clip = clip.with_effects([vfx.FadeIn(0.5)])

# 导入vfx模块
from moviepy import vfx
```

### ❌ 错误做法

```python
# 不要使用旧API
clip = clip.subclip(10, 20)  # MoviePy 1.x

# 不要直接调用效果函数
clip = clip.fadein(0.5)  # MoviePy 1.x
```

## 工具方法返回格式

所有工具方法返回统一的字典格式：

```python
{
    "success": True/False,
    "output_path": "/path/to/output.mp4",
    "duration": 20.5,
    "file_size_mb": 15.3,
    "error": "错误信息（失败时）"
}
```

## 错误处理

```python
result = tool.extract_clip(...)

if result["success"]:
    print(f"成功: {result['output_path']}")
else:
    print(f"失败: {result['error']}")
```

## 性能优化

1. **临时文件清理**：自动清理中间片段
2. **转场效果**：可选启用/禁用（影响处理时间）
3. **批处理**：一次性拼接多个片段

## 相关文件

- `app/tools/video_editing_tool.py` - 工具封装
- `app/agents/video_executor.py` - 执行Agent
- `app/utils/video_utils.py` - 底层工具函数
- `test_end_to_end_video.py` - 完整测试
