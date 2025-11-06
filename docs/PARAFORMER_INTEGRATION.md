# Paraformer语音识别集成文档

## 📋 概述

本项目已集成阿里云百炼Paraformer-v2语音识别服务，采用**异步处理方式**实现高效的视频语音转写功能。

## 🎯 核心特性

### 1. 异步处理架构
- ✅ 提交任务 → 轮询状态 → 获取结果的完整异步流程
- ✅ 支持长时间音频处理（最长12小时）
- ✅ 批量处理支持（单次最多100个文件）

### 2. 多语言支持
- ✅ 中文 (zh)
- ✅ 英文 (en)
- ✅ 日语 (ja)
- ✅ 韩语 (ko)
- ✅ 德语 (de)
- ✅ 法语 (fr)
- ✅ 俄语 (ru)

### 3. 高级功能
- ✅ 说话人分离 (Speaker Diarization)
- ✅ 时间戳标注 (精确到毫秒)
- ✅ 热词定制支持
- ✅ 自动标点符号

## 📁 集成架构

```
app/
├── utils/ai_clients/
│   ├── dashscope_client.py       # DashScope视觉分析
│   └── paraformer_client.py      # Paraformer语音识别 (新增)
├── services/
│   ├── video_analyzer.py         # 视频元数据分析
│   └── video_content_analyzer.py # 综合内容分析 (新增)
└── prompts/
    └── llm_prompts.py            # AudioTranscriptPrompts (新增)
```

## 🔧 使用方法

### 1. 基础用法 - 单文件识别

```python
from app.utils.ai_clients.paraformer_client import ParaformerClient

# 初始化客户端
paraformer = ParaformerClient()

# 识别音频（需要公网URL）
audio_url = "https://example.com/audio.wav"
result = await paraformer.transcribe_audio(
    file_url=audio_url,
    language_hints=["zh", "en"]
)

# 提取完整文本
text = paraformer.extract_full_text(result)
print(f"转写文本: {text}")

# 获取带时间戳的句子
sentences = paraformer.extract_sentences_with_timestamps(result)
for sentence in sentences:
    print(f"[{sentence['begin_time']}ms - {sentence['end_time']}ms] {sentence['text']}")
```

### 2. 启用说话人分离

```python
result = await paraformer.transcribe_audio(
    file_url=audio_url,
    language_hints=["zh"],
    enable_speaker_diarization=True,  # 启用说话人分离
    speaker_count=2                   # 预期说话人数量
)

# 格式化输出（包含说话人标识）
formatted_text = paraformer.format_transcript_for_llm(result)
print(formatted_text)
# 输出示例：
# [0.10s - 3.82s] [说话人0] 欢迎来到自动剪辑系统
# [4.20s - 7.50s] [说话人1] 谢谢，这个系统很棒
```

### 3. 批量识别多个文件

```python
audio_urls = [
    "https://example.com/audio1.wav",
    "https://example.com/audio2.wav",
    "https://example.com/audio3.wav"
]

results = await paraformer.transcribe_multiple(
    file_urls=audio_urls,
    language_hints=["zh", "en"]
)

for result in results:
    if "error" not in result:
        print(f"文件: {result['file_url']}")
        print(f"文本: {result['text']}")
    else:
        print(f"失败: {result['file_url']}, 错误: {result['error']}")
```

### 4. 综合视频内容分析

```python
from app.services.video_content_analyzer import VideoContentAnalyzer

analyzer = VideoContentAnalyzer()

# 完整分析（视觉 + 语音）
result = await analyzer.analyze_full_content(
    video_path="/path/to/video.mp4",          # 本地视频路径
    audio_url="https://oss.example.com/audio.wav",  # 音频公网URL
    enable_speech_recognition=True
)

# 访问分析结果
print("视觉分析:", result["visual_analysis"])
print("语音文本:", result["transcript_text"])
print("融合分析:", result["fusion_analysis"])

# 格式化为LLM输入
formatted_text = analyzer.format_analysis_for_llm(result)
```

### 5. 批量视频分析

```python
video_configs = [
    {
        "video_id": "vid_001",
        "video_path": "/path/to/video1.mp4",
        "audio_url": "https://oss.example.com/audio1.wav"
    },
    {
        "video_id": "vid_002",
        "video_path": "/path/to/video2.mp4",
        "audio_url": "https://oss.example.com/audio2.wav"
    }
]

results = await analyzer.analyze_batch_videos(
    video_configs=video_configs,
    enable_speech_recognition=True
)

for result in results:
    print(f"视频ID: {result['video_id']}")
    print(f"状态: {result['status']}")
    if result['status'] == 'success':
        print(f"视觉分析: {result['visual_analysis']}")
        print(f"语音文本: {result['transcript_text']}")
```

## 📊 音频文件要求

### 支持的格式
- 音频: aac, amr, flac, m4a, mp3, ogg, opus, wav, wma
- 视频: avi, flv, mkv, mov, mp4, mpeg, webm, wmv

### 文件限制
- **最大文件大小**: 2GB
- **最大时长**: 12小时
- **采样率**: paraformer-v2 支持任意采样率

### 文件访问方式

**重要**: Paraformer-v2 **仅支持公网可访问的HTTP/HTTPS URL**，不支持本地文件直传。

#### 方式1: 阿里云OSS（推荐）

```python
from oss2 import Auth, Bucket

# 上传到OSS
auth = Auth(access_key_id, access_key_secret)
bucket = Bucket(auth, endpoint, bucket_name)

# 上传音频文件
with open('audio.wav', 'rb') as f:
    bucket.put_object('audios/audio.wav', f)

# 设置公开读权限或生成签名URL
audio_url = f"https://{bucket_name}.{endpoint}/audios/audio.wav"

# 使用URL进行识别
result = await paraformer.transcribe_audio(audio_url)
```

#### 方式2: 从视频提取音频并上传

```python
from app.services.video_content_analyzer import VideoContentAnalyzer

analyzer = VideoContentAnalyzer()

# 提取音频
audio_path = await analyzer.extract_audio_for_recognition(
    video_path="/path/to/video.mp4",
    output_path="/tmp/audio.wav"
)

# 上传到OSS获得公网URL
audio_url = upload_to_oss(audio_path)

# 进行识别
result = await paraformer.transcribe_audio(audio_url)
```

## 🔄 异步处理流程

### 完整流程示意

```
1. 提交任务
   ↓
   async_call() → 返回task_id
   ↓
   状态: PENDING (排队中)

2. 等待处理
   ↓
   wait() 或循环 fetch()
   ↓
   状态: RUNNING (处理中)

3. 获取结果
   ↓
   状态: SUCCEEDED
   ↓
   下载 transcription_url 获取JSON结果
   ↓
   解析转写文本、时间戳、说话人信息
```

### 两种等待方式

#### 方式1: 同步等待（推荐）

```python
# Transcription.wait() 会阻塞直到完成
task_response = Transcription.async_call(
    model='paraformer-v2',
    file_urls=[audio_url]
)

# 等待完成（内部自动轮询）
result = Transcription.wait(task=task_response.output.task_id)
```

#### 方式2: 手动轮询

```python
task_response = Transcription.async_call(
    model='paraformer-v2',
    file_urls=[audio_url]
)

# 手动轮询状态
while True:
    status_response = Transcription.fetch(task=task_response.output.task_id)

    if status_response.output.task_status in ['SUCCEEDED', 'FAILED']:
        break

    await asyncio.sleep(5)  # 每5秒查询一次

# 处理结果
if status_response.output.task_status == 'SUCCEEDED':
    # 下载结果...
```

## 🎨 LLM提示词集成

### 语音转写提示词

```python
from app.prompts import AudioTranscriptPrompts

# 语音内容总结
prompt = AudioTranscriptPrompts.TRANSCRIPT_SUMMARY.format(
    transcript=transcript_text
)

# 音视频融合分析
prompt = AudioTranscriptPrompts.AUDIO_VISUAL_FUSION.format(
    visual_analysis=visual_text,
    transcript=transcript_text
)

# 使用LLM分析
result = await dashscope_client.chat(prompt)
```

## 📈 性能优化建议

### 1. 批量处理优化

```python
# ✅ 推荐：使用批量API
results = await paraformer.transcribe_multiple(
    file_urls=[url1, url2, url3, ...],  # 一次提交多个
    language_hints=["zh"]
)

# ❌ 避免：循环单独提交
for url in urls:
    result = await paraformer.transcribe_audio(url)  # 效率低
```

### 2. 并行分析多个视频

```python
# VideoContentAnalyzer 内部已实现并行
results = await analyzer.analyze_batch_videos(video_configs)
```

### 3. 缓存识别结果

```python
# 将识别结果缓存到Redis
import json
from app.utils.cache import cache_set, cache_get

cache_key = f"transcript:{video_id}"

# 尝试从缓存获取
cached_result = cache_get(cache_key)
if cached_result:
    return json.loads(cached_result)

# 缓存未命中，执行识别
result = await paraformer.transcribe_audio(audio_url)

# 缓存结果（24小时）
cache_set(cache_key, json.dumps(result), expire=86400)
```

## ⚠️ 常见问题

### 1. 文件无法下载错误

```
错误: InvalidFile.DownloadFailed
```

**原因**:
- URL不是公网可访问
- URL已过期（OSS签名URL有效期）
- 网络防火墙限制

**解决方案**:
- 确保使用公网HTTP/HTTPS URL
- 使用OSS公开读权限或生成新的签名URL
- 检查网络访问权限

### 2. 语言识别不准确

```python
# ❌ 未指定语言提示
result = await paraformer.transcribe_audio(audio_url)

# ✅ 明确指定语言
result = await paraformer.transcribe_audio(
    audio_url,
    language_hints=["zh"]  # 指定中文
)
```

### 3. 音频格式不支持

```
错误: InvalidFile.Format
```

**解决方案**: 使用FFmpeg转换为支持的格式

```python
import ffmpeg

# 转换为16kHz 单声道 WAV
stream = ffmpeg.input('input.mp3')
stream = ffmpeg.output(stream, 'output.wav',
                       acodec='pcm_s16le',
                       ar=16000,
                       ac=1)
ffmpeg.run(stream)
```

### 4. 任务超时

**正常情况**: 12小时音频可能需要数分钟处理

**处理方式**:
```python
# 设置合理的超时时间
try:
    result = await asyncio.wait_for(
        paraformer.transcribe_audio(audio_url),
        timeout=600  # 10分钟超时
    )
except asyncio.TimeoutError:
    logger.error("语音识别超时")
```

## 🔐 安全注意事项

### 1. API密钥保护

```bash
# .env 文件（不要提交到Git）
DASHSCOPE_API_KEY=sk-your-actual-key-here
```

### 2. OSS访问控制

```python
# 方式1: 使用签名URL（推荐）
from oss2 import SizedFileAdapter, determine_part_size

url = bucket.sign_url('GET', 'audios/audio.wav', 3600)  # 1小时有效

# 方式2: 仅对Paraformer服务IP开放
# 在OSS Bucket策略中配置IP白名单
```

### 3. 敏感内容处理

```python
# 对于包含敏感信息的音频
result = await paraformer.transcribe_audio(audio_url)

# 脱敏处理
transcript = result['text']
transcript = re.sub(r'\d{11}', '***手机号***', transcript)  # 脱敏手机号
transcript = re.sub(r'\d{6}', '***身份证***', transcript)  # 脱敏身份证
```

## 📊 成本估算

### Paraformer-v2 定价
- 按音频时长计费
- 详见阿里云百炼官网最新价格

### 成本优化建议
1. 使用批量API减少请求次数
2. 缓存识别结果避免重复识别
3. 合理使用语言提示提高识别准确率
4. 对于不需要精确时间戳的场景考虑使用实时识别API

## 📚 相关文档

- [阿里云百炼Paraformer文档](https://help.aliyun.com/zh/model-studio/developer-reference/paraformer-recorded-speech-recognition-python-api)
- [DashScope Python SDK](https://help.aliyun.com/zh/dashscope/developer-reference/python-sdk)
- [项目提示词管理](app/prompts/README.md)
- [视频分析服务](app/services/video_content_analyzer.py)

## 🤝 贡献指南

如需优化语音识别功能：

1. 调整提示词 → `app/prompts/llm_prompts.py`
2. 优化识别逻辑 → `app/utils/ai_clients/paraformer_client.py`
3. 改进融合分析 → `app/services/video_content_analyzer.py`

---

**集成完成时间**: 2024-01-01
**Paraformer模型**: paraformer-v2
**处理方式**: 异步 (Async Call + Wait/Fetch)
**状态**: ✅ 生产就绪
