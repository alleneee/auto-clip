# 视频/音频处理工具重构说明

## 📌 重构目标

将视频/音频处理操作从Service层解耦，抽取到独立的工具类中，实现：
- ✅ **关注点分离** - Service层专注业务编排，工具层专注技术实现
- ✅ **单一职责** - 每个函数只做一件事
- ✅ **可复用性** - 工具函数可在多个Service中复用
- ✅ **易测试性** - 纯函数易于单元测试
- ✅ **易维护性** - 技术实现集中管理，修改影响面小

## 🏗️ 新架构

### 分层架构

```
┌─────────────────────────────────────┐
│    Service层（业务编排）             │
│  - AudioExtractor                   │
│  - VideoCompressionService          │
│  - VideoEditingService              │
│  - VideoPreprocessor                │
└──────────────┬──────────────────────┘
               │ 调用
               ▼
┌─────────────────────────────────────┐
│    Utils层（底层工具）               │
│  - app/utils/video_utils.py         │
│  - app/utils/audio_utils.py         │
└─────────────────────────────────────┘
```

### 文件结构

```
app/
├── services/               # 业务服务层
│   ├── audio_extractor.py         # 音频提取服务（编排）
│   ├── video_compression.py       # 视频压缩服务（编排）
│   ├── video_editing.py           # 视频编辑服务（编排）
│   └── video_preprocessor.py     # 视频预处理服务（编排）
│
└── utils/                  # 底层工具层
    ├── video_utils.py             # 视频处理工具（纯函数）
    └── audio_utils.py             # 音频处理工具（纯函数）
```

## 🔧 工具函数列表

### video_utils.py - 视频处理工具

| 函数 | 功能 | 参数 |
|------|------|------|
| `get_video_metadata()` | 获取视频元数据 | video_path, ffprobe_path |
| `compress_video()` | 压缩视频 | input_path, output_path, bitrate, resolution, crf, preset |
| `extract_video_clip()` | 提取视频片段 | video_path, start_time, end_time, output_path |
| `concatenate_video_clips()` | 拼接视频 | clip_paths, output_path, method |
| `video_to_base64()` | 视频转base64 | video_path |

### audio_utils.py - 音频处理工具

| 函数 | 功能 | 参数 |
|------|------|------|
| `extract_audio_from_video()` | 从视频提取音频 | video_path, output_path, codec, fps, nbytes |
| `convert_audio_format()` | 转换音频格式 | input_path, output_path, format, bitrate |
| `merge_audio_files()` | 合并音频文件 | audio_paths, output_path, format |
| `trim_audio()` | 裁剪音频 | audio_path, output_path, start_time, end_time |

## 💡 重构示例

### 重构前 - Service层直接处理视频

```python
# app/services/audio_extractor.py (旧版)
class AudioExtractor:
    async def extract_audio(self, video_path: str, output_path: str) -> str:
        # 直接使用MoviePy进行音频处理
        from moviepy import VideoFileClip

        with VideoFileClip(video_path) as video:
            video.audio.write_audiofile(
                output_path,
                fps=16000,
                nbytes=2,
                codec='pcm_s16le',
                ffmpeg_params=["-ac", "1"]
            )

        return output_path
```

### 重构后 - Service层调用工具函数

```python
# app/services/audio_extractor.py (新版)
from app.utils.audio_utils import extract_audio_from_video

class AudioExtractor:
    async def extract_audio(self, video_path: str, output_path: str) -> str:
        # 调用底层工具函数，专注业务编排
        try:
            result_path = extract_audio_from_video(
                video_path=video_path,
                output_path=output_path,
                audio_codec='pcm_s16le',
                fps=16000,
                nbytes=2,
                ffmpeg_params=["-ac", "1"]
            )

            # 业务层验证和日志
            self._validate_output(result_path)
            logger.info("audio_extracted", path=result_path)

            return result_path

        except RuntimeError as e:
            # 业务异常转换
            raise AnalysisError(f"音频提取失败: {e}")
```

```python
# app/utils/audio_utils.py (工具层)
def extract_audio_from_video(
    video_path: str,
    output_path: str,
    audio_codec: str = "mp3",
    fps: Optional[int] = None,
    nbytes: Optional[int] = None,
    ffmpeg_params: Optional[list] = None
) -> str:
    """纯工具函数 - 只负责技术实现"""
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频不存在: {video_path}")

    with VideoFileClip(video_path) as video:
        if video.audio is None:
            raise RuntimeError("视频没有音轨")

        kwargs = {'codec': audio_codec}
        if fps: kwargs['fps'] = fps
        if nbytes: kwargs['nbytes'] = nbytes
        if ffmpeg_params: kwargs['ffmpeg_params'] = ffmpeg_params

        video.audio.write_audiofile(output_path, **kwargs)

    return output_path
```

## 📊 重构收益对比

| 维度 | 重构前 | 重构后 | 改进 |
|------|--------|--------|------|
| **职责清晰度** | Service层混杂技术实现 | Service层纯业务编排 | ⭐⭐⭐⭐⭐ |
| **代码复用** | 功能重复实现 | 工具函数统一复用 | ⭐⭐⭐⭐⭐ |
| **单元测试** | 需Mock业务依赖 | 纯函数直接测试 | ⭐⭐⭐⭐ |
| **可维护性** | 修改影响Service | 只修改工具层 | ⭐⭐⭐⭐⭐ |
| **可扩展性** | 需修改Service | 添加工具函数 | ⭐⭐⭐⭐ |

## 🔄 如何重构其他Service

### 步骤1: 识别底层操作

识别Service中直接调用的视频/音频处理代码：
- MoviePy操作
- ffmpeg命令
- 文件格式转换
- 元数据提取

### 步骤2: 抽取到工具函数

将底层操作移到 `video_utils.py` 或 `audio_utils.py`：

```python
# 从
class VideoCompressionService:
    def compress(self, input_path, output_path):
        subprocess.run(['ffmpeg', '-i', input_path, ...])

# 变成
# utils/video_utils.py
def compress_video(input_path, output_path, **kwargs):
    subprocess.run(['ffmpeg', '-i', input_path, ...])

# services/video_compression.py
class VideoCompressionService:
    def compress(self, input_path, output_path):
        return compress_video(input_path, output_path, crf=23)
```

### 步骤3: Service层专注编排

Service层只负责：
- 参数验证
- 业务逻辑判断
- 异常转换（技术异常 → 业务异常）
- 日志记录
- 状态管理

```python
class VideoCompressionService:
    async def compress_video(self, input_path, output_path, profile="balanced"):
        # 业务参数选择
        config = self._get_compression_config(profile)

        # 调用工具函数
        try:
            stats = compress_video(
                input_path, output_path,
                crf=config['crf'],
                preset=config['preset']
            )
        except RuntimeError as e:
            # 业务异常转换
            raise CompressionError(f"压缩失败: {e}")

        # 业务层验证和记录
        self._log_compression_stats(stats)
        return stats
```

## 🎯 设计原则

### 工具层（Utils）设计原则

1. **纯函数优先** - 无副作用，相同输入产生相同输出
2. **单一职责** - 每个函数只做一件事
3. **明确异常** - 抛出明确的异常类型（FileNotFoundError, RuntimeError等）
4. **无业务逻辑** - 不包含业务判断和状态管理
5. **可独立测试** - 不依赖外部状态

### 业务层（Service）设计原则

1. **编排为主** - 组合工具函数完成业务流程
2. **异常转换** - 将技术异常转换为业务异常
3. **业务验证** - 执行业务规则验证
4. **状态管理** - 管理业务状态和生命周期
5. **日志记录** - 记录业务操作和关键节点

## ✅ 迁移检查清单

- [ ] 所有视频压缩操作已抽取到 `video_utils.compress_video()`
- [ ] 所有音频提取操作已抽取到 `audio_utils.extract_audio_from_video()`
- [ ] 所有视频裁剪操作已抽取到 `video_utils.extract_video_clip()`
- [ ] 所有视频拼接操作已抽取到 `video_utils.concatenate_video_clips()`
- [ ] Service类只包含业务编排逻辑
- [ ] 工具函数已添加单元测试
- [ ] 文档已更新

## 📚 相关文档

- [SOLID原则](./SOLID_REFACTORING.md)
- [单元测试指南](./TESTING_GUIDE.md)
- [视频处理最佳实践](./VIDEO_PROCESSING_BEST_PRACTICES.md)
