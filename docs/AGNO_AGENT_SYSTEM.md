# Agno智能剪辑Agent系统

## 概述

基于Agno 2.x框架的多Agent智能视频剪辑系统，采用**专家团队协作模式**完成从视频分析到剪辑决策的全流程。

## 系统架构

### 四Agent工作流

```
ContentAnalyzer (内容分析专家)
    ↓ 输出: MultimodalAnalysis
CreativeStrategist (创意策略专家)
    ↓ 输出: CreativeStrategy
TechnicalPlanner (技术执行专家)
    ↓ 输出: TechnicalPlan
QualityReviewer (质量评审专家)
    ↓ 输出: QualityReview
```

### Agent职责分工

#### 1. ContentAnalyzer（内容分析专家）
- **技术栈**: Google Gemini 2.0 Flash Exp（多模态视觉+音频模型）
- **核心能力**: 视频全模态分析（视觉+音频+时间对齐）
- **输出数据**:
  - 时间轴片段（timeline）: 每段5-30秒，包含视觉、音频、情绪、重要性
  - 关键时刻（key_moments）: 3-5个高潜力剪辑点，标注视觉/音频高潮
  - 语音转录（transcription）: 逐句转录+时间戳（如有人声）
  - 音频层次（audio_layers）: 语音/音乐/静音分段

**重要实现细节**: 
- 使用Google原生`upload_file()` API上传视频
- 等待处理完成后再传入Agent（`while video_file.state.name == "PROCESSING"`）
- 用`Video(content=video_file)`包装上传的文件
- **不使用OpenRouter**，直接用Google API（OpenRouter不支持视频输入）

#### 2. CreativeStrategist（创意策略专家）
- **技术栈**: DeepSeek Chat（高推理能力，经济实惠）
- **核心能力**: 基于内容分析生成创意策略
- **输出数据**:
  - 目标平台（target_platform）: YouTube Shorts/抖音/Instagram Reels
  - 叙事角度（narrative_angle）: 故事化包装方式
  - 情绪曲线（emotional_arc）: 起承转合设计
  - Hook策略（hook_strategy）: 开头3秒吸引策略

#### 3. TechnicalPlanner（技术执行专家）
- **技术栈**: DeepSeek Chat
- **核心能力**: 将创意策略转化为技术执行计划
- **输出数据**:
  - 剪辑点列表（clip_points）: 精确时间戳 + 剪辑动作
  - 转场效果（transitions）: 每个片段的转场类型
  - 音频处理（audio_processing）: 音量调整、音效添加
  - 字幕配置（subtitle_config）: 样式、位置、时长

#### 4. QualityReviewer（质量评审专家）
- **技术栈**: DeepSeek Chat
- **核心能力**: 5维度质量评分 + 改进建议
- **输出数据**:
  - 内容质量分（content_quality）: 1-10分
  - 技术执行分（technical_execution）: 1-10分
  - 创意新颖度（creative_novelty）: 1-10分
  - 平台适配度（platform_fit）: 1-10分
  - 病毒潜力（viral_potential）: 0-1概率
  - 改进建议（improvement_suggestions）: 具体可操作的优化点

## API密钥配置

### 1. Google Gemini API密钥

**获取步骤**:
1. 访问 Google AI Studio: https://aistudio.google.com/app/apikey
2. 使用Google账号登录
3. 点击"Create API Key"
4. 复制密钥（格式: `AIzaSy...`）

**配置方式**:
```bash
# 在.env文件中添加
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

**注意事项**:
- Gemini API有免费配额（每分钟15次请求，每天1500次）
- 视频分析需要gemini-2.0-flash-exp或更高版本
- 视频大小限制: 最大2GB，最长2小时

### 2. DeepSeek API密钥

**获取步骤**:
1. 访问 DeepSeek 开放平台: https://platform.deepseek.com/
2. 注册并登录账号
3. 进入"API Keys"页面
4. 创建新的API密钥
5. 复制密钥（格式: `sk-...`）

**配置方式**:
```bash
# 在.env文件中添加
DEEPSEEK_API_KEY=sk-eb2e45cc436a440bbb606f588ebbc094
```

**成本优势**:
- DeepSeek Chat: ¥1/百万tokens（输入），¥2/百万tokens（输出）
- 相比GPT-4便宜20-30倍
- 推理能力强，特别适合策略和规划任务

## 快速开始

### 1. 安装依赖

```bash
pip install agno python-dotenv rich google-generativeai
```

### 2. 配置环境变量

```bash
# 复制示例配置
cp .env.example .env

# 编辑.env文件，填入API密钥
GEMINI_API_KEY=your_gemini_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
```

### 3. 测试ContentAnalyzer（单Agent）

```bash
python test_agno_real_video.py
```

**预期输出**:
```
🧪 ContentAnalyzerAgent 真实视频测试
======================================================================

📹 测试视频: /Users/niko/Desktop/7537292399417658639.mp4
🤖 模型: gemini-2.0-flash-exp
🔑 API Key: AIzaSyXXXXXXXXXX...

🔄 创建ContentAnalyzerAgent...
✅ Agent创建成功

🔄 开始视频分析（使用Google原生文件上传）...
   上传视频到Google AI...
   等待视频处理...
   视频处理完成

✅ 视频分析成功！
======================================================================

📊 分析结果:
   - 视频ID: test_desktop_video
   - 时长: 58.2秒
   - 时间轴片段: 6个
   - 关键时刻: 4个
```

### 4. 测试完整工作流（四Agent协作）

```bash
python test_agno_with_desktop_video.py
```

**预期输出**:
```
🧪 Agno智能剪辑Agent系统测试
======================================================================

Step 1/4: ContentAnalyzer 分析视频...
✅ Step 1 完成

Step 2/4: CreativeStrategist 生成创意策略...
✅ Step 2 完成

Step 3/4: TechnicalPlanner 制定执行计划...
✅ Step 3 完成

Step 4/4: QualityReviewer 质量评审...
✅ Step 4 完成

🎉 完整工作流测试成功！
```

## 数据模型

### MultimodalAnalysis（多模态分析结果）

```python
{
    "video_id": "test_video",
    "duration": 58.2,
    "timeline": [
        {
            "start": 0.0,
            "end": 15.0,
            "visual": "办公室场景，人物坐在电脑前",
            "audio": "轻柔的背景音乐，无语音",
            "emotion": "calm",
            "importance": 3,
            "sync_quality": "medium"
        }
    ],
    "key_moments": [
        {
            "timestamp": 25.5,
            "visual_peak": true,
            "audio_peak": true,
            "sync_type": "emphasis",
            "description": "特写镜头配合强调语气",
            "clip_potential": 0.95
        }
    ],
    "transcription": [
        {
            "start": 10.0,
            "end": 15.0,
            "text": "这个方法可以节省50%的时间",
            "confidence": 0.95
        }
    ],
    "audio_layers": {
        "speech_segments": [[10, 30], [45, 60]],
        "music_segments": [[0, 10], [60, 90]],
        "silence_segments": [],
        "dominant_layer": "speech"
    }
}
```

## 技术亮点

### 1. 原生多模态视频分析
- 直接上传视频到Google AI，无需预处理
- 音视频对齐分析，识别关键时刻
- 自动语音转录（如有人声）

### 2. 专家团队协作模式
- 每个Agent专注单一职责
- 步骤式工作流（Workflow），自动传递上下文
- 结构化数据交互（Pydantic模型）

### 3. 混合模型策略
- Gemini: 多模态分析（强项是视觉+音频理解）
- DeepSeek: 策略和规划（成本低，推理能力强）
- 总成本: 约¥0.1-0.2/分钟视频

### 4. 生产级错误处理
- 视频上传失败自动重试
- JSON解析多重回退策略
- 详细日志（structlog）

## 常见问题

### Q1: Gemini API返回"Video input is currently unsupported"

**原因**: 使用了OpenRouter而不是Google原生API

**解决方案**: 
- ✅ 使用 `agno.models.google.Gemini`
- ✅ 用 `google.generativeai.upload_file()` 上传视频
- ❌ 不要用OpenRouter（它不支持视频输入）

### Q2: 视频分析失败"File is still processing"

**原因**: 上传后立即使用，Google还在处理视频

**解决方案**: 添加等待循环
```python
video_file = upload_file(video_path)
while video_file.state.name == "PROCESSING":
    time.sleep(2)
    video_file = get_file(video_file.name)
```

### Q3: DeepSeek API报错"API key not found"

**解决方案**: 
1. 检查.env文件是否正确配置 `DEEPSEEK_API_KEY`
2. 确保运行前加载了环境变量 `load_dotenv()`
3. 验证密钥格式（必须以 `sk-` 开头）

### Q4: 成本控制建议

**优化策略**:
- Gemini免费配额：每天1500次，先用免费额度
- DeepSeek极低成本：¥1-2/百万tokens
- 缓存分析结果：避免重复分析同一视频
- 批量处理：一次性分析多个视频

## 下一步计划

- [ ] 添加更多平台适配（B站、快手）
- [ ] 支持批量视频处理
- [ ] 集成视频编辑执行（MoviePy）
- [ ] Web UI界面
- [ ] Agent记忆系统（跨会话学习）

## 参考文档

- Agno官方文档: https://docs.agno.com
- Google AI Studio: https://aistudio.google.com
- DeepSeek开放平台: https://platform.deepseek.com
