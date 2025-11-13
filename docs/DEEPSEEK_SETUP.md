# DeepSeek API 配置指南

## 为什么选择DeepSeek？

DeepSeek是一款性价比极高的大语言模型：

- 💰 **超低成本**：$0.14/M tokens（约为GPT-4o的1/50）
- 🚀 **响应快速**：推理速度快，适合生产环境
- 🧠 **质量优秀**：文本推理能力接近GPT-4
- 🇨🇳 **中文友好**：对中文理解和生成非常出色

在auto-clip的Agno Agent系统中，DeepSeek用于：
- CreativeStrategistAgent（创意策略制定）
- TechnicalPlannerAgent（技术方案规划）
- QualityReviewerAgent（质量评审）

这三个Agent主要处理文本推理任务，使用DeepSeek可以将成本从**$0.50降至$0.02**（每个60秒视频）。

## 获取DeepSeek API密钥

### 方案A：通过OpenRouter访问（推荐⭐）

**OpenRouter** 是统一API网关，单一密钥即可访问DeepSeek、GPT、Claude等多个模型：

**优势**：
- ✅ **一键多模型**：一个API密钥访问所有主流LLM
- ✅ **无需翻墙**：国内可直接访问
- ✅ **按需付费**：充值后按实际使用扣费
- ✅ **LiteLLM兼容**：完全兼容LiteLLM接口

**使用步骤**：

1. 访问：https://openrouter.ai/
2. 注册并登录
3. 进入"Keys"页面创建API密钥
4. 充值（支持信用卡）
5. 配置环境变量：

```bash
# 设置OpenRouter密钥
export OPENROUTER_API_KEY="sk-or-v1-xxxxx"

# 也需要Gemini密钥（用于视频分析）
export GEMINI_API_KEY="your_gemini_key"
```

6. 运行时指定模型：

```python
from app.agents import AgnoClipTeam

team = AgnoClipTeam(
    analyzer_model="gemini/gemini-2.0-flash-exp",
    strategist_model="openrouter/deepseek/deepseek-chat",
    planner_model="openrouter/deepseek/deepseek-chat",
    reviewer_model="openrouter/deepseek/deepseek-chat",
    api_keys={
        "analyzer": os.getenv("GEMINI_API_KEY"),
        "strategist": os.getenv("OPENROUTER_API_KEY"),
        "planner": os.getenv("OPENROUTER_API_KEY"),
        "reviewer": os.getenv("OPENROUTER_API_KEY")
    }
)
```

**支持的模型示例**（通过OpenRouter访问）：
- `openrouter/deepseek/deepseek-chat` - DeepSeek对话模型
- `openrouter/anthropic/claude-3.5-sonnet` - Claude 3.5
- `openrouter/openai/gpt-4o` - GPT-4o
- `openrouter/google/gemini-pro` - Gemini Pro

---

### 方案B：直接使用DeepSeek官方API

如果希望直接使用DeepSeek官方服务：

#### 1. 注册账号

访问：https://platform.deepseek.com/

点击右上角"注册"按钮，使用邮箱注册。

#### 2. 创建API密钥

1. 登录后，进入"API Keys"页面
2. 点击"Create new secret key"
3. 给密钥命名（如"auto-clip-agno"）
4. 复制生成的API密钥（格式：`sk-xxxxxxxxxx`）

⚠️ **重要**：API密钥只显示一次，务必立即保存！

#### 3. 充值（如需要）

DeepSeek提供免费额度，如果需要更多使用量：

1. 进入"Billing"页面
2. 选择充值金额（支持支付宝、微信支付）
3. 最低充值$5，足够处理数千个视频

#### 4. 配置环境变量

**macOS/Linux**

```bash
# 临时设置（当前终端有效）
export DEEPSEEK_API_KEY="sk-xxxxxxxxxx"

# 永久设置（添加到~/.bashrc或~/.zshrc）
echo 'export DEEPSEEK_API_KEY="sk-xxxxxxxxxx"' >> ~/.zshrc
source ~/.zshrc
```

**Windows**

```powershell
# PowerShell
$env:DEEPSEEK_API_KEY="sk-xxxxxxxxxx"

# 永久设置（系统环境变量）
# 右键"此电脑" → 属性 → 高级系统设置 → 环境变量
# 新建用户变量：DEEPSEEK_API_KEY = sk-xxxxxxxxxx
```

**.env文件（推荐）**

在项目根目录创建`.env`文件：

```bash
# .env
DEEPSEEK_API_KEY=sk-xxxxxxxxxx
GEMINI_API_KEY=your_gemini_key
```

## 验证配置

### 使用OpenRouter的验证

如果你使用OpenRouter，运行以下代码：

```python
import os
from litellm import completion

# 检查环境变量
api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    print("❌ OPENROUTER_API_KEY未设置")
    exit(1)

print(f"✅ OPENROUTER_API_KEY已设置: {api_key[:15]}...")

# 测试通过OpenRouter调用DeepSeek
try:
    response = completion(
        model="openrouter/deepseek/deepseek-chat",
        messages=[{"role": "user", "content": "你好，请用一句话介绍你自己"}],
        api_key=api_key
    )
    print("✅ OpenRouter + DeepSeek API调用成功")
    print(f"响应: {response.choices[0].message.content}")
except Exception as e:
    print(f"❌ API调用失败: {e}")
```

保存为`test_openrouter.py`，运行：
```bash
python test_openrouter.py
```

---

### 使用DeepSeek官方API的验证

如果你使用DeepSeek官方API，运行以下代码：

```python
import os
from litellm import completion

# 检查环境变量
api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    print("❌ DEEPSEEK_API_KEY未设置")
    exit(1)

print(f"✅ DEEPSEEK_API_KEY已设置: {api_key[:10]}...")

# 测试API调用
try:
    response = completion(
        model="deepseek/deepseek-chat",
        messages=[{"role": "user", "content": "你好，请用一句话介绍你自己"}],
        api_key=api_key
    )
    print("✅ DeepSeek API调用成功")
    print(f"响应: {response.choices[0].message.content}")
except Exception as e:
    print(f"❌ DeepSeek API调用失败: {e}")
```

保存为`test_deepseek.py`，运行：
```bash
python test_deepseek.py
```

## 完整配置示例

### 使用OpenRouter（推荐）

配置好OpenRouter和Gemini后，运行Agno Agent系统：

```bash
# 1. 设置API密钥
export GEMINI_API_KEY="your_gemini_key"
export OPENROUTER_API_KEY="sk-or-v1-xxxxx"

# 2. 运行演示
python agno_clip_demo.py video.mp4 --duration 60

# 3. 查看输出
# 应该看到：
# 🤖 初始化Agent团队...
#   • 内容分析: Gemini 2.0 Flash
#   • 创意策略: OpenRouter/DeepSeek Chat
#   • 技术规划: OpenRouter/DeepSeek Chat
#   • 质量评审: OpenRouter/DeepSeek Chat
# ✅ Agent团队初始化完成
```

**注意**：如果使用OpenRouter，需要在代码中显式指定API密钥，或修改默认配置。

---

### 使用DeepSeek官方API

配置好DeepSeek和Gemini后，运行Agno Agent系统：

```bash
# 1. 设置API密钥
export GEMINI_API_KEY="your_gemini_key"
export DEEPSEEK_API_KEY="your_deepseek_key"

# 2. 运行演示
python agno_clip_demo.py video.mp4 --duration 60

# 3. 查看输出
# 应该看到：
# 🤖 初始化Agent团队...
#   • 内容分析: Gemini 2.0 Flash
#   • 创意策略: DeepSeek Chat
#   • 技术规划: DeepSeek Chat
#   • 质量评审: DeepSeek Chat
# ✅ Agent团队初始化完成
```

## 常见问题

### Q: DeepSeek免费额度是多少？

A: DeepSeek通常提供一定的免费额度，具体以官网为准。免费额度用完后需要充值。

### Q: DeepSeek支持哪些模型？

A: 主要模型：
- `deepseek-chat`（通用对话）⭐ 推荐
- `deepseek-coder`（代码生成）

在LiteLLM中使用时需加前缀：`deepseek/deepseek-chat`

### Q: DeepSeek API调用失败怎么办？

A: 检查以下几点：
1. API密钥是否正确设置（`echo $DEEPSEEK_API_KEY`）
2. 是否有网络问题（DeepSeek服务器在国内，一般无需代理）
3. 是否有余额（登录平台查看）
4. 模型名称是否正确（`deepseek/deepseek-chat`）

### Q: 可以不用DeepSeek吗？

A: 可以！系统支持多种模型组合：

```python
from app.agents import AgnoClipTeam

# 使用GPT-4o（成本高）
team = AgnoClipTeam(
    strategist_model="gpt-4o",
    planner_model="gpt-4o",
    reviewer_model="gpt-4o"
)

# 使用Claude（创意任务优秀）
team = AgnoClipTeam(
    strategist_model="claude-3-5-sonnet",
    planner_model="claude-3-5-sonnet",
    reviewer_model="claude-3-5-sonnet"
)
```

但从性价比角度，强烈推荐DeepSeek！

## 成本对比

60秒视频剪辑方案生成（单次）：

| 模型组合 | 成本 | 说明 |
|---------|------|------|
| Gemini + DeepSeek | ~$0.02 | ⭐ 推荐 |
| Gemini + GPT-4o | ~$0.50 | 质量最高 |
| Gemini + GPT-4o-mini | ~$0.05 | 中等成本 |

如果每天处理100个视频：
- DeepSeek：**$2/天** = $60/月
- GPT-4o：**$50/天** = $1500/月
- GPT-4o-mini：**$5/天** = $150/月

**节省成本**: 使用DeepSeek每月可节省**$1440**！🎉

## 技术支持

- DeepSeek官方文档：https://platform.deepseek.com/docs
- LiteLLM文档：https://docs.litellm.ai/docs/providers/deepseek
- 问题反馈：提交Issue到auto-clip仓库

---

**提示**：配置完DeepSeek后，建议先用`agno_clip_demo.py`测试一个短视频，确认系统运行正常后再批量使用。
