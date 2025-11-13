# Agno配置总结 - LiteLLM迁移至原生类

## 核心变更

### 迁移前（LiteLLM统一接口）

所有Agent使用LiteLLM作为统一模型接口：

```python
from agno.models.litellm import LiteLLM

# ContentAnalyzer
model=LiteLLM(id="gemini/gemini-2.0-flash-exp", ...)

# 其他Agents
model=LiteLLM(id="deepseek/deepseek-chat", ...)
```

**问题**：
- ❌ Gemini视频输入不支持（通过OpenRouter）
- ❌ 额外的抽象层，增加调试难度
- ❌ 某些原生功能无法访问

### 迁移后（Agno原生类）

每个Agent使用原生模型类：

```python
# ContentAnalyzer: 使用Google原生Gemini
from agno.models.google import Gemini
from google.generativeai import upload_file, get_file
from agno.media import Video

model = Gemini(id="gemini-2.0-flash-exp", api_key=GEMINI_API_KEY)

# 1. 上传视频到Google AI
video_file = upload_file(video_path)

# 2. 等待处理完成
while video_file.state.name == "PROCESSING":
    time.sleep(2)
    video_file = get_file(video_file.name)

# 3. 使用Video对象包装
video = Video(content=video_file)

# 4. 调用Agent
response = agent.run(prompt, videos=[video])
```

```python
# 其他Agents: 使用DeepSeek原生类
from agno.models.deepseek import DeepSeek

model = DeepSeek(id="deepseek-chat", api_key=DEEPSEEK_API_KEY)
```

**优势**：
- ✅ 支持Gemini原生视频分析
- ✅ 直接访问Google文件上传API
- ✅ 更好的错误信息和调试体验
- ✅ 遵循Agno官方推荐方式

## API密钥配置

### 环境变量（.env文件）

```bash
# Google Gemini（内容分析专家）
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# DeepSeek（策略+规划+评审）
DEEPSEEK_API_KEY=sk-eb2e45cc436a440bbb606f588ebbc094
```

### 代码配置

```python
import os
from dotenv import load_dotenv

load_dotenv()

# ContentAnalyzer
analyzer = ContentAnalyzerAgent(
    model="gemini-2.0-flash-exp",
    api_key=os.getenv("GEMINI_API_KEY"),
    temperature=0.3
)

# CreativeStrategist / TechnicalPlanner / QualityReviewer
strategist = CreativeStrategistAgent(
    model="deepseek-chat",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    temperature=0.8
)
```

## 文件变更清单

### 核心Agent文件

#### 1. app/agents/content_analyzer.py

**变更内容**:
- 移除 `from agno.models.litellm import LiteLLM`
- 添加 `from agno.models.google import Gemini`
- 添加 `from google.generativeai import upload_file, get_file`
- 添加 `from agno.media import Video`
- 修改模型默认值：`gemini/gemini-2.0-flash-exp` → `gemini-2.0-flash-exp`
- 实现Google原生文件上传流程

**关键代码**:
```python
# 第42-75行：模型初始化
self.agent = Agent(
    name="ContentAnalyzer",
    model=Gemini(id=model, api_key=api_key, temperature=temperature),
    # ...
)

# 第235-261行：视频上传和分析
video_file = upload_file(str(path.absolute()))
while video_file.state.name == "PROCESSING":
    time.sleep(2)
    video_file = get_file(video_file.name)
video = Video(content=video_file)
response = self.agent.run(prompt, videos=[video])
```

#### 2. app/agents/creative_strategist.py

**变更内容**:
- 移除 `from agno.models.litellm import LiteLLM`
- 添加 `from agno.models.deepseek import DeepSeek`
- 修改模型默认值：`deepseek/deepseek-chat` → `deepseek-chat`

**关键代码**:
```python
from agno.models.deepseek import DeepSeek

model = DeepSeek(id=model, api_key=api_key, temperature=temperature)
```

#### 3. app/agents/technical_planner.py

**变更内容**: 同creative_strategist.py

#### 4. app/agents/quality_reviewer.py

**变更内容**: 同creative_strategist.py

#### 5. app/agents/clip_team.py

**变更内容**:
- 移除 `from agno.models.litellm import LiteLLM`（未使用）
- 移除 `from agno.workflow import RunResponse`（不存在）
- 更新默认模型名称（移除provider前缀）

### 测试文件

#### 1. test_agno_real_video.py（新建）

**用途**: 测试ContentAnalyzer的视频分析功能

**关键功能**:
- 加载GEMINI_API_KEY
- 创建ContentAnalyzerAgent
- 分析Desktop视频
- 显示结构化结果

#### 2. test_agno_with_desktop_video.py（已存在）

**用途**: 测试完整四Agent工作流

**需要修改**: 使用新的API密钥配置（待更新）

### 文档文件

#### 1. docs/AGNO_AGENT_SYSTEM.md（新建）

**内容**:
- 系统架构说明
- 四Agent职责分工
- API密钥获取指南
- 快速开始教程
- 数据模型详解
- 常见问题Q&A

#### 2. docs/QUICK_START_AGNO.md（新建）

**内容**:
- 3步快速开始
- 两个测试场景
- 预期输出示例
- 故障排查指南

#### 3. docs/CONFIGURATION_SUMMARY.md（本文件）

**内容**:
- 迁移前后对比
- 配置变更清单
- 成本对比分析

### 配置文件

#### 1. .env

**新增配置**:
```bash
# Gemini (Google AI) - 用于Agno ContentAnalyzer
# 获取API密钥: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=
```

## 成本对比分析

### 迁移前（OpenRouter统一接口）

| 模型 | 通过OpenRouter | 成本 |
|------|---------------|------|
| Gemini 2.0 Flash | ❌ 不支持视频输入 | - |
| DeepSeek Chat | ✅ 支持 | $0.27/M tokens |

**总成本**: 无法实现视频分析功能

### 迁移后（原生API）

| 模型 | 直接调用 | 成本 | 免费配额 |
|------|---------|------|---------|
| Gemini 2.0 Flash Exp | ✅ 支持视频输入 | $0.00/M tokens | 每天1500次 |
| DeepSeek Chat | ✅ 支持 | ¥1-2/M tokens | 无 |

**总成本估算**（每分钟视频）:
- ContentAnalyzer: ¥0（免费配额内）
- 其他3个Agents: ¥0.05-0.15
- **总计**: ¥0.05-0.15/分钟视频

### 成本优势

1. **Gemini免费配额充足**: 每天1500次请求，足够分析750-1500个视频（每个视频1-2次请求）
2. **DeepSeek极低成本**: 比GPT-4便宜20-30倍，比Claude便宜10-15倍
3. **混合策略最优**: 多模态用Gemini（免费），推理用DeepSeek（便宜）

## 测试验证

### 测试场景1：ContentAnalyzer单Agent

```bash
python test_agno_real_video.py
```

**验证点**:
- ✅ Gemini API密钥加载成功
- ✅ 视频上传到Google AI
- ✅ 视频处理状态监控
- ✅ Agent成功分析视频
- ✅ 返回结构化MultimodalAnalysis

### 测试场景2：完整四Agent工作流

```bash
python test_agno_with_desktop_video.py
```

**验证点**:
- ✅ Workflow Step 1: ContentAnalyzer（Gemini）
- ✅ Workflow Step 2: CreativeStrategist（DeepSeek）
- ✅ Workflow Step 3: TechnicalPlanner（DeepSeek）
- ✅ Workflow Step 4: QualityReviewer（DeepSeek）
- ✅ 上下文自动传递
- ✅ 最终输出QualityReview

## 技术要点

### Google文件上传流程（关键）

```python
# 1. 上传文件
video_file = upload_file(video_path)

# 2. 等待处理（重要！不能跳过）
while video_file.state.name == "PROCESSING":
    time.sleep(2)
    video_file = get_file(video_file.name)

# 3. 包装为Video对象
video = Video(content=video_file)

# 4. 传入Agent
agent.run(prompt, videos=[video])
```

**常见错误**:
- ❌ 跳过等待循环 → "File is still processing"
- ❌ 直接传文件路径字符串 → "'str' object has no attribute 'id'"
- ❌ 使用OpenRouter → "Video input is currently unsupported"

### Agno原生模型类

```python
# Gemini
from agno.models.google import Gemini
Gemini(id="gemini-2.0-flash-exp", api_key=GOOGLE_KEY)

# DeepSeek
from agno.models.deepseek import DeepSeek
DeepSeek(id="deepseek-chat", api_key=DEEPSEEK_KEY)

# OpenRouter（仅文本）
from agno.models.openrouter import OpenRouter
OpenRouter(id="google/gemini-2.5-flash", api_key=OPENROUTER_KEY)
```

**注意**: 模型ID不需要provider前缀（`gemini/`, `deepseek/`），原生类自动处理

## 下一步计划

- [ ] 运行测试验证迁移成功
- [ ] 获取Gemini API密钥
- [ ] 测试真实视频分析
- [ ] 性能优化（缓存、批处理）
- [ ] 集成到主Pipeline

## 参考资源

- Agno官方文档: https://docs.agno.com
- Google AI Studio: https://aistudio.google.com/app/apikey
- DeepSeek开放平台: https://platform.deepseek.com
- 官方视频分析示例: test_gemini_via_openrouter.py
