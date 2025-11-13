# 完整视频生产工作流快速入门

## 🎯 概述

完整视频生产工作流是Auto-Clip最新实现的一体化功能，可以从多个原始视频素材自动生成带口播旁白的完整视频。

**一键完成**:
- ✅ 多视频AI分析
- ✅ 智能剪辑方案
- ✅ 视频片段提取
- ✅ 自动脚本生成
- ✅ TTS语音合成
- ✅ 音视频混合
- ✅ 质量评分输出

## 🚀 快速开始

### 最简单的使用方式

```bash
# 发送API请求
curl -X POST http://localhost:8000/api/v1/batch/process \
  -H "Content-Type: application/json" \
  -d '{
    "video_paths": [
      "/path/to/video1.mp4",
      "/path/to/video2.mp4"
    ],
    "config": {
      "add_narration": true
    }
  }'

# 返回任务ID
{
  "task_id": "batch_xxx",
  "status": "processing"
}
```

### 使用Python客户端

```python
import asyncio
import httpx

async def create_video():
    async with httpx.AsyncClient(timeout=600) as client:
        # 发起请求
        response = await client.post(
            "http://localhost:8000/api/v1/batch/process",
            json={
                "video_paths": [
                    "/path/to/video1.mp4",
                    "/path/to/video2.mp4"
                ],
                "config": {
                    "add_narration": True,
                    "narration_voice": "longxiaochun",
                    "target_duration": 60
                }
            }
        )
        result = response.json()
        task_id = result["task_id"]

        # 轮询任务状态
        while True:
            status_response = await client.get(
                f"http://localhost:8000/api/v1/tasks/{task_id}/status"
            )
            status = status_response.json()

            if status["status"] == "completed":
                print(f"视频生成完成: {status['final_video']['url']}")
                break
            elif status["status"] == "failed":
                print(f"生成失败: {status['error']}")
                break

            await asyncio.sleep(10)

asyncio.run(create_video())
```

## ⚙️ 配置选项

### 必需配置

```python
{
  "add_narration": true  # 启用完整生产流程
}
```

### 完整配置示例

```python
{
  # === 核心配置 ===
  "add_narration": true,  # 是否添加口播（启用完整流程）
  "narration_voice": "longxiaochun",  # TTS语音类型

  # === 音频配置 ===
  "background_music_path": "/path/to/music.mp3",  # 背景音乐
  "background_music_volume": 0.2,  # 背景音乐音量 (0-1)

  # === 视频配置 ===
  "target_duration": 60,  # 目标时长（秒）
  "min_clip_duration": 2.0,  # 最小片段时长（秒）
  "transition_type": "crossfade",  # 转场类型

  # === 质量配置 ===
  "quality_threshold": 0.7  # 质量阈值（0-1）
}
```

### TTS语音选项

可用的语音类型：
- `longxiaochun`: 龙小春（亲切、适合Vlog）
- `zhimi`: 知米（正式、适合教学）
- `zhifeng_emo`: 知枫（情感丰富）
- `zhimiao_emo`: 知喵（活泼）

### 转场类型

可用的转场效果：
- `fade`: 淡入淡出（默认）
- `crossfade`: 交叉淡化
- `slide`: 滑动
- `zoom`: 缩放
- `rotate`: 旋转
- `wipe`: 擦除

## 📊 输出结果

### 成功响应

```json
{
  "task_id": "batch_20240101_123456",
  "status": "completed",

  "final_video": {
    "url": "https://xxx.oss.com/final_video_with_narration.mp4",
    "path": "/storage/final_video_with_narration.mp4",
    "duration": 62.5
  },

  "script": {
    "full_text": "各位观众大家好，今天我们来看...",
    "segments": [
      {
        "text": "各位观众大家好",
        "duration": 2.5,
        "start_time": 0.0
      },
      ...
    ]
  },

  "quality_scores": {
    "narrative_coherence": 0.92,
    "audio_video_sync": 0.88,
    "content_coverage": 0.85,
    "production_quality": 0.90,
    "engagement_potential": 0.87,
    "overall_score": 0.88
  },

  "statistics": {
    "source_videos": 2,
    "total_clips": 8,
    "total_duration": 62.5,
    "narration_duration": 58.3,
    "processing_time": 245.6
  }
}
```

### 质量评分说明

| 指标 | 说明 | 权重 |
|------|------|------|
| narrative_coherence | 脚本与视频内容的匹配度 | 30% |
| audio_video_sync | 音频与视频的同步质量 | 25% |
| content_coverage | 视频内容的完整性 | 20% |
| production_quality | 制作质量（音频混合、转场） | 15% |
| engagement_potential | 整体吸引力和观看体验 | 10% |

**总分计算**: `overall_score = Σ(指标 × 权重)`

## 🎬 使用场景

### 1. 自媒体创作

```python
# 多个素材快速成片
config = {
    "add_narration": True,
    "narration_voice": "longxiaochun",
    "background_music_path": "upbeat.mp3",
    "background_music_volume": 0.25,
    "target_duration": 180,
    "transition_type": "crossfade"
}
```

### 2. 教育视频

```python
# 课程素材自动讲解
config = {
    "add_narration": True,
    "narration_voice": "zhimi",  # 正式语音
    "target_duration": 300,
    "min_clip_duration": 5.0,
    "background_music_path": "calm.mp3",
    "background_music_volume": 0.15
}
```

### 3. 新闻快讯

```python
# 快速生成新闻解说
config = {
    "add_narration": True,
    "narration_voice": "zhimi",
    "target_duration": 90,
    "min_clip_duration": 3.0
}
```

### 4. Vlog制作

```python
# 旅行素材故事化
config = {
    "add_narration": True,
    "narration_voice": "longxiaochun",
    "background_music_path": "travel.mp3",
    "background_music_volume": 0.2,
    "target_duration": 240,
    "transition_type": "crossfade"
}
```

## 🔧 高级功能

### 自定义脚本主题

通过分析结果可以影响脚本生成：

```python
# 在config中添加主题提示
config = {
    "add_narration": True,
    "script_theme": "科技评测",  # 可选：指定脚本主题
    "script_style": "专业",      # 可选：指定脚本风格
}
```

### 质量控制

```python
config = {
    "add_narration": True,
    "quality_threshold": 0.8,  # 设置更高的质量要求
    "retry_on_low_quality": True  # 低质量时自动重试
}
```

## 🐛 故障排查

### 常见问题

**1. 任务一直处于 processing 状态**
- 检查Celery Worker是否正常运行
- 查看Worker日志：`docker-compose logs -f worker-analyzer`
- 确认Redis连接正常

**2. 生成的视频没有声音**
- 检查 `add_narration: true` 是否设置
- 确认DashScope API密钥配置正确
- 查看TTS服务日志确认是否有错误

**3. 脚本内容与视频不匹配**
- 检查视频分析结果是否完整
- 尝试调整 `target_duration` 参数
- 增加源视频数量以提供更多素材

**4. 音频混合效果不理想**
- 调整 `background_music_volume` 参数
- 确认背景音乐文件格式正确
- 尝试不同的音乐文件

### 日志查看

```bash
# 查看API日志
docker-compose logs -f api

# 查看Worker日志
docker-compose logs -f worker-analyzer
docker-compose logs -f worker-clipper

# 查看特定任务日志
docker-compose logs | grep "task_id"
```

## 📚 完整示例

使用提供的演示脚本：

```bash
# 运行交互式演示
python examples/complete_video_production_demo.py

# 选择演示场景:
# 1. 基础口播视频生成
# 2. 带背景音乐的完整视频
# 3. 教育视频自动生成
# 4. Vlog自动制作
# 5. 工作流对比
```

## 🔗 相关文档

- 完整架构说明: `docs/VIDEO_PROCESSING_PIPELINE.md` (流程 2.5)
- API文档: http://localhost:8000/api/v1/docs
- 项目总览: `CLAUDE.md`

## 💡 最佳实践

1. **视频素材选择**
   - 提供3-5个不同场景的视频效果最佳
   - 单个视频时长建议30-120秒
   - 确保视频内容有关联性

2. **配置优化**
   - 首次使用建议采用默认配置
   - 根据输出质量评分逐步调整参数
   - 背景音乐音量建议0.15-0.25

3. **性能优化**
   - 使用 `hybrid` 存储模式提升性能
   - 启用Redis任务存储保证可靠性
   - 合理设置 `target_duration` 避免过长处理时间

4. **质量保证**
   - 查看质量评分各维度指标
   - 低于0.7分建议调整配置重新生成
   - 关注 `narrative_coherence` 确保内容匹配

## 🎯 下一步

- 尝试不同的TTS语音类型
- 实验各种转场效果
- 调整背景音乐配置
- 使用更多视频素材
- 探索高级配置选项

---

**需要帮助？** 查看完整文档或提交Issue: https://github.com/your-repo/auto-clip/issues
