# Kokoro TTS 集成文档

## 📖 简介

Kokoro 是一个开源的轻量级TTS（文本转语音）模型，具有以下特点：

- **轻量级**: 仅82M参数，远小于商业TTS模型
- **高速**: 本地运行，推理速度快
- **多语言**: 支持8种语言（包括中文）
- **开源**: Apache许可证，可商用
- **无需API**: 本地运行，无需联网和API密钥

## 🚀 安装

### 1. 安装Python包

```bash
pip install kokoro>=0.9.4 soundfile
```

### 2. 安装espeak-ng（必需）

**Linux/WSL:**
```bash
sudo apt-get install espeak-ng
```

**macOS:**
```bash
brew install espeak
```

**Windows:**
从 [espeak-ng releases](https://github.com/espeak-ng/espeak-ng/releases) 下载并安装 `.msi` 文件。

### 3. 可选：安装pydub（用于MP3转换）

```bash
pip install pydub
# 还需要ffmpeg
# macOS: brew install ffmpeg
# Linux: sudo apt-get install ffmpeg
```

## 🎯 支持的语言

Kokoro使用单字母代码表示语言：

| 语言代码 | 语言 | 标准代码 |
|---------|------|---------|
| `a` | 美式英语 | `en-US` |
| `b` | 英式英语 | `en-GB` |
| `e` | 西班牙语 | `es` |
| `f` | 法语 | `fr` |
| `h` | 印地语 | `hi` |
| `i` | 意大利语 | `it` |
| `j` | 日语 | `ja` |
| `p` | 巴西葡萄牙语 | `pt-BR` |
| `z` | 中文 | `zh-CN` |

**注意**: KokoroTTSAdapter会自动将标准语言代码（如`zh-CN`）转换为Kokoro代码（如`z`）。

## 🎨 音色列表

Kokoro支持多种音色（voice），常见的有：

### 英语音色
- `af_heart` - 女声，温暖
- `af_sky` - 女声，清新
- `am_adam` - 男声，沉稳
- `am_michael` - 男声，活力

### 中文音色（待验证）
Kokoro对中文的音色支持可能有限，建议测试后使用。

## 🔧 配置

### 环境变量（.env）

```bash
# Kokoro TTS配置
KOKORO_VOICE=af_heart        # 默认音色
KOKORO_LANG=z                # 默认语言代码（z=中文）
KOKORO_SPEED=1.0             # 默认语速（0.5-2.0）
```

### 配置文件（app/config.py）

配置已集成到 `Settings` 类中：

```python
KOKORO_VOICE: str = "af_heart"
KOKORO_LANG: str = "z"
KOKORO_SPEED: float = 1.0  # 0.5-2.0范围
```

## 💻 使用方法

### 1. 在AgnoClipTeam中使用

```python
from app.agents import AgnoClipTeam

# 创建团队时指定Kokoro TTS
team = AgnoClipTeam(
    analyzer_model="gemini-2.5-flash",
    strategist_model="qwen-max",
    planner_model="qwen-max",
    reviewer_model="qwen-max",
    analyzer_provider="gemini",
    text_provider="dashscope",
    tts_provider="kokoro",  # 使用Kokoro TTS
    enable_video_execution=True,
    enable_narration=True,
    temp_dir="tmp"
)

# 运行工作流
config = {
    "target_duration": 30,
    "platform": "douyin",
    "add_narration": True,
    "narration_voice": "af_heart",  # Kokoro音色
    "narration_speed": 1.1,          # 语速控制
    "generate_srt": True,
    "burn_subtitles": True,
}

output = await team.run(
    video_paths=["video1.mp4", "video2.mp4"],
    config=config,
    output_path="output/final.mp4"
)
```

### 2. 直接使用KokoroTTSAdapter

```python
from app.adapters.kokoro_tts_adapter import KokoroTTSAdapter

# 初始化
adapter = KokoroTTSAdapter(
    default_voice="af_heart",
    default_lang="zh-CN",
    default_speed=1.0
)

# 生成音频（返回字节流）
audio_bytes = await adapter.synthesize_speech(
    text="你好，这是一个测试。",
    voice="af_heart",
    lang="zh-CN",
    speed=1.2
)

# 保存到文件
await adapter.synthesize_to_file(
    text="你好，这是一个测试。",
    output_path="output/test.wav",
    voice="af_heart",
    lang="zh-CN"
)
```

### 3. 多语言示例

```python
# 英语
audio_en = await adapter.synthesize_speech(
    text="Hello, this is a test.",
    voice="af_heart",
    lang="en-US"
)

# 中文
audio_zh = await adapter.synthesize_speech(
    text="你好，这是一个测试。",
    voice="af_heart",
    lang="zh-CN"
)

# 日语
audio_ja = await adapter.synthesize_speech(
    text="こんにちは、これはテストです。",
    voice="af_heart",
    lang="ja"
)
```

## 🧪 测试

运行测试脚本验证安装：

```bash
python test_kokoro_tts.py
```

测试内容包括：
1. ✅ 基础音频合成
2. ✅ 多语言支持
3. ✅ 语速控制
4. ✅ 保存到文件
5. ✅ 性能测试

## 📊 性能对比

| TTS提供商 | 延迟 | 质量 | 成本 | 依赖 |
|----------|------|------|------|------|
| **Kokoro** | 极低（本地） | 中等 | 免费 | 本地模型 |
| **Edge TTS** | 低 | 高 | 免费 | 网络 |
| **DashScope** | 中 | 非常高 | 按量付费 | API密钥+网络 |

**推荐场景**:
- **开发测试**: Kokoro（快速、免费、无需网络）
- **高质量生产**: DashScope或Edge TTS
- **离线场景**: Kokoro（唯一选择）
- **多语言**: Edge TTS或Kokoro

## ⚙️ 技术细节

### 音频规格

- **采样率**: 24kHz（固定）
- **格式**: 默认WAV，可选MP3（需要pydub）
- **声道**: 单声道
- **位深度**: 16-bit PCM

### 内存需求

- **模型大小**: ~82MB
- **运行内存**: ~200MB（首次加载）
- **音频缓存**: 根据文本长度动态分配

### 性能指标

- **初始化时间**: 1-2秒（首次）
- **生成速度**: ~50-100字符/秒（取决于硬件）
- **并发支持**: 支持异步并发生成

## 🐛 故障排除

### 问题1: ImportError: No module named 'kokoro'

**解决方案**:
```bash
pip install kokoro>=0.9.4 soundfile
```

### 问题2: espeak-ng not found

**解决方案**:
- Linux: `sudo apt-get install espeak-ng`
- macOS: `brew install espeak`
- Windows: 下载并安装 `.msi` 文件

### 问题3: 中文发音不准确

**原因**: Kokoro对中文的支持可能不如英语
**解决方案**:
- 调整语速: `speed=0.9`
- 尝试不同音色
- 考虑使用Edge TTS或DashScope

### 问题4: MP3转换失败

**原因**: pydub或ffmpeg未安装
**解决方案**:
```bash
pip install pydub
# macOS
brew install ffmpeg
# Linux
sudo apt-get install ffmpeg
```

### 问题5: Mac M系列芯片性能问题

**解决方案**: 设置环境变量启用GPU加速
```bash
export PYTORCH_ENABLE_MPS_FALLBACK=1
```

## 🔄 从其他TTS迁移

### 从Edge TTS迁移

```python
# 之前
team = AgnoClipTeam(
    tts_provider="edge",
    ...
)

# 现在
team = AgnoClipTeam(
    tts_provider="kokoro",
    ...
)
```

### 从DashScope迁移

```python
# 之前
config = {
    "narration_voice": "longxiaochun",  # DashScope音色
    ...
}

# 现在
config = {
    "narration_voice": "af_heart",  # Kokoro音色
    ...
}
```

## 📝 最佳实践

1. **开发环境**: 使用Kokoro（快速、免费、离线）
2. **生产环境**: 根据质量要求选择
   - 高质量: DashScope
   - 平衡: Edge TTS
   - 离线: Kokoro
3. **多语言项目**: Edge TTS（支持最广）
4. **音色选择**: 测试后固定使用，避免频繁切换
5. **错误处理**: 在ScriptGeneratorAgent中已自动处理Kokoro初始化失败，会回退到其他TTS

## 🔗 参考资源

- [Kokoro GitHub](https://github.com/hexgrad/kokoro)
- [Kokoro 文档](https://github.com/hexgrad/kokoro#readme)
- [espeak-ng 官网](https://github.com/espeak-ng/espeak-ng)

## 📄 许可证

Kokoro TTS 使用 Apache 2.0 许可证，可商用。

---

**更新日期**: 2025-01-13
**维护者**: Auto-Clip Team
