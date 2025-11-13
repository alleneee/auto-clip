# Agno框架集成DashScope VL模型指南

## 🎯 核心问题

**如何使用agno框架上传本地视频文件到DashScope VL模型进行解析？**

## 💡 三种实现方案

### 方案1：直接使用DashScope官方SDK（⭐推荐）

**特点**：
- ✅ 最简单，项目已完全集成
- ✅ 官方维护，稳定可靠
- ✅ 支持base64编码上传本地文件
- ❌ 不是通过agno框架调用

**使用方式**：

```python
from app.utils.ai_clients.dashscope_client import DashScopeClient
import base64

# 1. 初始化客户端
client = DashScopeClient()

# 2. 读取本地视频并编码
with open("/path/to/video.mp4", "rb") as f:
    video_base64 = base64.b64encode(f.read()).decode("utf-8")

# 3. 调用DashScope VL模型分析
result = await client.analyze_video_visual_base64(
    video_base64=video_base64,
    prompt="请详细分析这个视频的内容"
)

print(result)
```

**代码位置**：`app/utils/ai_clients/dashscope_client.py:81-135`

---

### 方案2：通过Agno Tool包装DashScope（⭐适合Agent系统）

**特点**：
- ✅ 符合agno框架规范
- ✅ 可集成到任何Agno Agent
- ✅ 支持Tool调用链
- ⚠️ 需要封装少量代码

**实现步骤**：

#### Step 1: 定义Agno Tool

```python
from agno.tools import tool
from app.utils.ai_clients.dashscope_client import DashScopeClient
import base64
import asyncio
from pathlib import Path

@tool
def analyze_video_dashscope(
    video_path: str,
    prompt: str = "请详细分析这个视频的内容"
) -> str:
    """
    使用DashScope qwen-vl-plus模型分析本地视频

    Args:
        video_path: 本地视频文件路径
        prompt: 分析提示词

    Returns:
        视频分析结果
    """
    try:
        # 验证文件
        path = Path(video_path)
        if not path.exists():
            return f"错误：视频文件不存在 - {video_path}"

        # 读取并编码视频
        with open(path, "rb") as f:
            video_base64 = base64.b64encode(f.read()).decode("utf-8")

        # 调用DashScope客户端
        client = DashScopeClient()
        result = asyncio.run(
            client.analyze_video_visual_base64(
                video_base64=video_base64,
                prompt=prompt
            )
        )

        return result

    except Exception as e:
        return f"视频分析失败: {str(e)}"
```

#### Step 2: 创建Agent并集成Tool

```python
from agno.agent import Agent
from agno.models.google import Gemini

# 创建Agent（使用Gemini作为大脑，DashScope作为视频分析工具）
agent = Agent(
    name="VideoAnalyzer",
    model=Gemini(id="gemini-2.0-flash-exp"),
    tools=[analyze_video_dashscope],  # 集成DashScope Tool
    instructions=[
        "你是专业的视频分析专家",
        "当用户提供视频路径时，使用analyze_video_dashscope工具分析",
        "分析结果要详细、结构化"
    ],
    markdown=False
)

# 使用Agent分析视频
response = agent.run("请分析这个视频的内容：/path/to/video.mp4")
print(response.content)
```

**架构图**：

```
用户请求 → Agno Agent (Gemini大脑)
              ↓
         调用Tool: analyze_video_dashscope
              ↓
         DashScopeClient (qwen-vl-plus)
              ↓
         base64上传本地视频
              ↓
         返回分析结果
```

---

### 方案3：使用LiteLLM中间层（⚠️实验性）

**特点**：
- ✅ 统一多模型接口
- ✅ 支持模型切换
- ⚠️ LiteLLM对DashScope VL模型支持有限
- ⚠️ 需要额外配置

**实现方式**：

```python
from app.tools.litellm_multimodal_tool import LiteLLMMultimodalTool

# 注意：需要LiteLLM支持dashscope视频输入
tool = LiteLLMMultimodalTool(
    model="dashscope/qwen-vl-plus",
    api_key=os.getenv("DASHSCOPE_API_KEY")
)

# 分析视频
result = await tool.analyze_video(
    video_path="/path/to/video.mp4",
    prompt="请分析视频内容"
)
```

**代码位置**：`app/tools/litellm_multimodal_tool.py`

**注意事项**：
- LiteLLM对DashScope视频支持尚不完善
- 推荐先使用方案1或方案2
- 适合需要多模型切换的场景

---

## 🚀 快速开始

### 环境准备

1. **安装依赖**：

```bash
pip install agno python-dotenv rich dashscope google-generativeai
```

2. **配置环境变量**（`.env`文件）：

```bash
# 必填：DashScope API密钥
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxx

# 可选：Gemini API密钥（方案2需要，用于Agent大脑）
GEMINI_API_KEY=AIzaSyxxxxxxxxxxxxxx
```

### 运行演示

```bash
# 运行完整演示（三种方案对比）
python examples/agno_dashscope_video_demo.py

# 选择：
# 1 - 方案1演示（推荐，最简单）
# 2 - 方案2演示（Agno Agent集成）
# 3 - 方案3演示（实验性）
# 0 - 运行所有方案
```

---

## 📊 方案对比

| 方案 | 难度 | Agno集成 | 推荐度 | 适用场景 |
|------|------|----------|--------|----------|
| 方案1: DashScope SDK | 简单 | ❌ | ⭐⭐⭐⭐⭐ | 纯视频分析 |
| 方案2: Agno Tool | 中等 | ✅ | ⭐⭐⭐⭐ | Agent系统 |
| 方案3: LiteLLM | 复杂 | ✅ | ⭐⭐ | 多模型切换 |

---

## 💡 使用建议

### 场景1：只需要视频分析
→ **使用方案1**（最简单，直接用SDK）

```python
from app.utils.ai_clients.dashscope_client import DashScopeClient
import base64

client = DashScopeClient()

with open("video.mp4", "rb") as f:
    video_base64 = base64.b64encode(f.read()).decode("utf-8")

result = await client.analyze_video_visual_base64(
    video_base64=video_base64,
    prompt="分析视频"
)
```

### 场景2：需要Agent协作系统
→ **使用方案2**（Agno框架集成）

```python
from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools import tool

# 定义Tool（见上文）
@tool
def analyze_video_dashscope(video_path: str, prompt: str) -> str:
    # ... 实现代码 ...
    pass

# 创建Agent
agent = Agent(
    name="VideoAnalyzer",
    model=Gemini(id="gemini-2.0-flash-exp"),
    tools=[analyze_video_dashscope]
)

# 运行
response = agent.run("分析 /path/to/video.mp4")
```

### 场景3：需要多模型切换
→ **使用方案3**（开发中，谨慎使用）

---

## 🔍 技术细节

### DashScope VL模型支持的输入方式

1. **网络URL方式**（`analyze_video_visual`）：
   - 视频必须是公网可访问的URL
   - 如OSS签名URL：`https://xxx.oss-cn-beijing.aliyuncs.com/video.mp4?sign=xxx`
   - 适合已上传到云存储的视频

2. **Base64编码方式**（`analyze_video_visual_base64`）：
   - 支持本地视频文件
   - 将视频转换为base64编码后传输
   - 适合临时分析、不需要持久化存储的场景

### 为什么DashScope不像Gemini那样原生支持文件上传？

- **Gemini**: 使用Google AI原生`upload_file()` API，上传文件到Google服务器
- **DashScope**: 使用阿里云API，支持URL和base64两种方式，**不提供文件上传API**
- **解决方案**: 通过base64编码方式实现本地文件"上传"

### Agno框架中的Tool机制

```python
@tool  # Agno装饰器，将函数注册为可调用工具
def my_tool(arg1: str, arg2: int) -> str:
    """
    工具描述（Agent会读取这个docstring）

    Args:
        arg1: 参数1描述
        arg2: 参数2描述

    Returns:
        返回值描述
    """
    # 实现逻辑
    return result
```

**Agent如何使用Tool**：
1. Agent收到用户请求
2. 分析请求，决定是否需要调用Tool
3. 调用Tool并传入参数
4. 整合Tool返回结果，生成最终回复

---

## 🎬 完整示例：四Agent协作系统

项目已实现的完整工作流（参考`agno_clip_demo.py`）：

```
ContentAnalyzer (Gemini 2.0) - 视频分析
        ↓
CreativeStrategist (DeepSeek) - 创意策略
        ↓
TechnicalPlanner (DeepSeek) - 技术方案
        ↓
QualityReviewer (DeepSeek) - 质量评审
```

**运行完整工作流**：

```bash
python agno_clip_demo.py video1.mp4 video2.mp4 --duration 60 --platform douyin
```

---

## 🐛 常见问题

### Q1: DashScope API返回"视频格式不支持"

**解决方案**：
- 确保视频是mp4格式
- 压缩视频大小（建议<50MB）
- 使用项目的视频预处理服务：`app/services/video_preprocessing_service.py`

### Q2: Base64编码后视频太大导致超时

**解决方案**：
```python
from app.services.video_preprocessing_service import video_preprocessing_service

# 先压缩视频
compressed_path = await video_preprocessing_service.compress_video(
    video_path="/path/to/large_video.mp4",
    target_size_mb=10  # 压缩到10MB
)

# 再分析
with open(compressed_path, "rb") as f:
    video_base64 = base64.b64encode(f.read()).decode("utf-8")
```

### Q3: Agno Agent没有调用DashScope Tool

**可能原因**：
1. Tool的docstring描述不清楚
2. Agent的instructions没有明确指示使用Tool
3. 用户请求不明确

**解决方案**：
```python
agent = Agent(
    name="VideoAnalyzer",
    model=Gemini(id="gemini-2.0-flash-exp"),
    tools=[analyze_video_dashscope],
    instructions=[
        "当用户提供视频路径（如.mp4文件）时，必须使用analyze_video_dashscope工具",
        "工具会自动处理视频上传和分析",
        "不要尝试自己分析视频，必须调用工具"
    ]
)
```

### Q4: 如何切换到Gemini进行视频分析？

**方案**：使用项目已有的`ContentAnalyzerAgent`（支持Gemini原生视频上传）

```python
from app.agents.content_analyzer import ContentAnalyzerAgent

# 使用Gemini分析（原生上传，无需base64）
analyzer = ContentAnalyzerAgent(
    model="gemini-2.0-flash-exp",
    provider="gemini"  # 使用Gemini provider
)

result = analyzer.analyze(
    video_path="/path/to/video.mp4",
    video_id="test_video"
)

print(result.model_dump_json(indent=2))
```

**代码位置**：`app/agents/content_analyzer.py:252-313`

---

## 📚 相关文档

- [Agno Agent系统完整指南](./AGNO_AGENT_SYSTEM.md)
- [Gemini集成指南](./GEMINI_INTEGRATION.md)
- [视频处理Pipeline](./VIDEO_PROCESSING_PIPELINE.md)
- [完整工作流快速开始](./COMPLETE_WORKFLOW_QUICK_START.md)

---

## 🤝 技术支持

如有问题，请：
1. 查看演示脚本：`examples/agno_dashscope_video_demo.py`
2. 运行测试：`python test_agent_real_workflow.py`
3. 提交Issue到项目仓库

---

**最后更新**：2025-11-12
**作者**：Auto-Clip Team
