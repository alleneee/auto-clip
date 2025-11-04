# VL + ASR 音视频融合分析与切分完整流程

## 概述

本文档说明如何使用 MoviePy 提取音频，结合 VL 视觉模型和 ASR 语音识别模型，进行音视频融合分析，最终完成视频智能切分。

## 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                        输入：视频文件                          │
└─────────────────────────────────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
                ▼                       ▼
    ┌──────────────────┐    ┌──────────────────┐
    │  VL 视觉分析      │    │  音频提取         │
    │  qwen-vl-plus    │    │  MoviePy 2.x     │
    │  (本地视频)       │    │  → 16kHz WAV     │
    └──────────────────┘    └──────────────────┘
                │                       │
                │                       ▼
                │           ┌──────────────────┐
                │           │  上传到公网URL     │
                │           └──────────────────┘
                │                       │
                │                       ▼
                │           ┌──────────────────┐
                │           │  ASR 语音识别     │
                │           │  Paraformer-v2   │
                │           │  (带时间戳)       │
                │           └──────────────────┘
                │                       │
                └───────────┬───────────┘
                            ▼
                ┌──────────────────┐
                │  融合分析         │
                │  qwen-plus       │
                │  (文本模型)       │
                └──────────────────┘
                            │
                            ▼
                ┌──────────────────┐
                │  切分决策         │
                │  (时间点+理由)    │
                └──────────────────┘
                            │
                            ▼
                ┌──────────────────┐
                │  视频切分         │
                │  MoviePy 2.x     │
                └──────────────────┘
                            │
                            ▼
                ┌──────────────────┐
                │  输出：剪辑片段    │
                └──────────────────┘
```

## 核心组件

### 1. VideoContentAnalyzer - 音视频融合分析器

**文件**: `app/services/video_content_analyzer.py`

#### 主要方法

##### `analyze_full_content()` - 完整内容分析

并行执行 VL 视觉分析和 ASR 语音识别，然后进行融合分析。

```python
async def analyze_full_content(
    self,
    video_path: str,              # 本地视频文件路径
    audio_url: Optional[str] = None,  # 音频公网URL（ASR用）
    enable_speech_recognition: bool = True,
    visual_prompt: Optional[str] = None,
) -> Dict[str, Any]:
```

**返回结构**:
```python
{
    "visual_analysis": "视觉内容描述...",
    "transcript": {
        "text": "完整转写文本",
        "sentences": [
            {
                "text": "句子内容",
                "begin_time": 1000,  # 毫秒
                "end_time": 3500,
                "speaker_id": 0  # 说话人ID（如果启用）
            }
        ]
    },
    "transcript_text": "完整转写文本",
    "has_speech": true,
    "fusion_analysis": "融合分析结果...",
    "status": "success",
    "errors": []
}
```

##### `extract_audio_for_recognition()` - 音频提取（使用 MoviePy）

**改进点**: ✅ 现在使用 **MoviePy 2.x** 替代 ffmpeg-python

```python
async def extract_audio_for_recognition(
    self,
    video_path: str,    # 输入视频
    output_path: str    # 输出音频（建议 .wav）
) -> str:
```

**音频格式规格**（符合 Paraformer 要求）:
- 采样率: 16kHz
- 声道: 单声道
- 编码: PCM 16位

### 2. ParaformerClient - ASR 语音识别

**文件**: `app/utils/ai_clients/paraformer_client.py`

##### `transcribe_audio()` - 语音识别

```python
async def transcribe_audio(
    self,
    file_url: str,  # ⚠️ 必须是公网URL
    model: str = "paraformer-v2",
    language_hints: Optional[List[str]] = None,  # ['zh', 'en']
    enable_speaker_diarization: bool = False,  # 说话人分离
) -> Dict[str, Any]:
```

**重要**: Paraformer 服务只接受公网 URL，不支持本地文件。

### 3. DashScopeClient - VL 视觉分析

**文件**: `app/utils/ai_clients/dashscope_client.py`

##### `analyze_video_visual()` - 视觉分析

```python
async def analyze_video_visual(
    self,
    video_path: str,  # 本地视频文件路径
    prompt: Optional[str] = None
) -> str:
```

### 4. VideoEditingService - 视频切分

**文件**: `app/services/video_editing.py`

##### `extract_clip()` - 提取片段

```python
async def extract_clip(
    self,
    video_path: str,
    start_time: float,  # 秒
    end_time: float,    # 秒
    output_path: Optional[str] = None
) -> str:
```

##### `process_clip_plan()` - 批量切分

```python
async def process_clip_plan(
    self,
    video_paths: List[str],
    segments: List[ClipSegment],  # 切分方案
    output_path: str,
    output_quality: str = 'high'
) -> Tuple[str, Dict[str, Any]]:
```

## 完整使用示例

### 场景 1: 单视频完整分析与切分

```python
from app.services.video_content_analyzer import VideoContentAnalyzer
from app.services.video_editing import VideoEditingService
from app.models.batch_processing import ClipSegment
import tempfile
import os

async def analyze_and_clip_video(video_path: str):
    """完整的分析和切分流程"""

    # 1. 初始化服务
    analyzer = VideoContentAnalyzer()
    editor = VideoEditingService()

    # 2. 使用 MoviePy 提取音频
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_audio:
        audio_path = tmp_audio.name

    audio_file = await analyzer.extract_audio_for_recognition(
        video_path=video_path,
        output_path=audio_path
    )

    print(f"✅ 音频已提取: {audio_file}")

    # 3. 上传音频到OSS获取公网URL（此处需要你的OSS上传逻辑）
    # audio_url = await upload_to_oss(audio_file)
    audio_url = "https://your-oss-bucket.com/audio.wav"  # 示例URL

    # 4. 并行执行 VL + ASR 分析
    analysis_result = await analyzer.analyze_full_content(
        video_path=video_path,
        audio_url=audio_url,
        enable_speech_recognition=True
    )

    # 5. 检查分析结果
    if analysis_result["status"] != "success":
        print(f"❌ 分析失败: {analysis_result['errors']}")
        return

    print("✅ 视觉分析:", analysis_result["visual_analysis"][:100], "...")
    print("✅ 语音识别:", analysis_result["transcript_text"][:100], "...")
    print("✅ 融合分析:", analysis_result["fusion_analysis"][:100], "...")

    # 6. 格式化结果用于LLM（生成切分决策）
    formatted_input = analyzer.format_analysis_for_llm(analysis_result)

    # 7. 调用LLM生成切分方案（这里需要你的LLM决策逻辑）
    # 假设返回切分片段列表
    segments = [
        ClipSegment(
            video_index=0,
            start_time=10.5,
            end_time=25.8,
            priority=1.0,
            reason="精彩内容：讲解核心知识点"
        ),
        ClipSegment(
            video_index=0,
            start_time=45.2,
            end_time=60.1,
            priority=0.9,
            reason="高潮部分：演示关键操作"
        )
    ]

    # 8. 执行视频切分
    output_path = os.path.join(tempfile.gettempdir(), "final_output.mp4")

    final_video, stats = await editor.process_clip_plan(
        video_paths=[video_path],
        segments=segments,
        output_path=output_path,
        output_quality='high'
    )

    print(f"✅ 视频切分完成: {final_video}")
    print(f"   片段数: {stats['segment_count']}")
    print(f"   总时长: {stats['total_duration']:.2f}秒")
    print(f"   文件大小: {stats['output_size_mb']:.2f}MB")

    # 9. 清理临时文件
    os.remove(audio_file)

    return final_video, analysis_result, stats
```

### 场景 2: 批量视频分析

```python
async def batch_analyze_videos(video_configs: List[Dict]):
    """批量分析多个视频"""

    analyzer = VideoContentAnalyzer()

    # 准备配置（包含音频URL）
    configs_with_audio = []

    for config in video_configs:
        # 提取音频
        audio_path = f"/tmp/{config['video_id']}_audio.wav"
        await analyzer.extract_audio_for_recognition(
            config['video_path'],
            audio_path
        )

        # 上传获取URL
        audio_url = await upload_to_oss(audio_path)

        configs_with_audio.append({
            "video_id": config['video_id'],
            "video_path": config['video_path'],
            "audio_url": audio_url
        })

    # 批量分析（并行执行）
    results = await analyzer.analyze_batch_videos(
        configs_with_audio,
        enable_speech_recognition=True
    )

    return results
```

## 关键注意事项

### ✅ 已改进

1. **音频提取统一使用 MoviePy 2.x**
   - 与视频剪辑服务保持一致
   - 符合 Paraformer ASR 音频格式要求
   - 自动处理无音频视频的情况

### ⚠️ 需要注意

1. **Paraformer 需要公网 URL**
   ```python
   # ❌ 不支持
   transcribe_audio(file_url="file:///local/path/audio.wav")

   # ✅ 正确
   transcribe_audio(file_url="https://your-cdn.com/audio.wav")
   ```

2. **音频上传流程**
   - 使用 `extract_audio_for_recognition()` 提取本地音频
   - 上传到 OSS/CDN 获取公网 URL
   - 传递 URL 给 Paraformer

3. **资源清理**
   - 及时清理临时音频文件
   - 使用 `with` 语句管理 VideoFileClip

4. **错误处理**
   - 检查视频是否包含音频轨道
   - 处理 ASR 识别失败的情况
   - 验证 VL 分析结果

## 性能优化建议

1. **并行处理**
   ```python
   # analyze_full_content() 已经并行执行 VL + ASR
   # 批量处理时可以进一步并行
   tasks = [analyze_full_content(v) for v in videos]
   results = await asyncio.gather(*tasks)
   ```

2. **音频缓存**
   - 如果同一视频需要多次分析，可以缓存提取的音频
   - 缓存 ASR 识别结果

3. **质量权衡**
   - 高质量视频用 'high' 质量输出
   - 预览用途可用 'medium' 或 'low'

## 故障排查

### 问题 1: MoviePy 导入错误

```bash
# 确保安装 MoviePy 2.x
pip install "moviepy>=2.0.0,<3.0.0"

# 验证版本
python -c "import moviepy; print(moviepy.__version__)"
```

### 问题 2: 音频提取失败

```python
# 检查视频是否有音频
from moviepy import VideoFileClip
with VideoFileClip(video_path) as v:
    print(f"Has audio: {v.audio is not None}")
```

### 问题 3: Paraformer 识别失败

```python
# 检查音频URL是否可访问
import httpx
async with httpx.AsyncClient() as client:
    resp = await client.head(audio_url)
    print(f"Status: {resp.status_code}")
```

## 相关文档

- [MoviePy 2.x 文档](https://zulko.github.io/moviepy/)
- [阿里云 DashScope API](https://help.aliyun.com/zh/dashscope/)
- [Paraformer 语音识别](https://help.aliyun.com/zh/dashscope/developer-reference/paraformer-api)

## 更新日志

### 2024-11-04
- ✅ 使用 MoviePy 2.x 替代 ffmpeg-python 提取音频
- ✅ 音频格式优化，符合 Paraformer 要求
- ✅ 完善错误处理和日志记录
- ✅ 添加文件验证和资源清理
