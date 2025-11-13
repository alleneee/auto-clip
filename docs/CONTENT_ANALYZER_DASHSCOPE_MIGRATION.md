# ContentAnalyzerAgent 迁移到 DashScope

## 📝 修改摘要

**日期**: 2025-11-12
**目标**: 将 ContentAnalyzerAgent 从 Gemini/OpenRouter 迁移到纯 DashScope qwen-vl 模型

---

## ✅ 完成的修改

### 1. 移除的依赖

```python
# ❌ 移除
from agno.models.google import Gemini
from agno.models.openrouter import OpenRouter
from google.generativeai import upload_file, get_file
```

### 2. 新增的依赖

```python
# ✅ 新增
from agno.models.dashscope import DashScope
```

### 3. 简化的初始化方法

#### 修改前 (Before)

```python
def __init__(
    self,
    model: str = "gemini-2.0-flash-exp",
    api_key: str = None,
    temperature: float = 0.3,
    provider: Literal["gemini", "openrouter"] = "gemini"  # 多个provider
):
    if provider == "openrouter":
        model_instance = OpenRouter(...)
    else:  # gemini
        model_instance = Gemini(...)
```

#### 修改后 (After)

```python
def __init__(
    self,
    model: str = "qwen-vl-plus",  # ✅ 改为 DashScope 模型
    api_key: Optional[str] = None,
    temperature: float = 0.3
):
    # ✅ 直接创建 DashScope 实例
    model_instance = DashScope(
        id=model,
        api_key=api_key,
        temperature=temperature
    )
```

### 4. 简化的视频分析流程

#### 修改前 (Before)

```python
def analyze(self, video_path: str, video_id: str = None):
    if self.provider == "openrouter":
        # OpenRouter 逻辑
        video = Video(filepath=str(path.absolute()))
        response = self.agent.run(prompt, videos=[video])

    else:  # gemini
        # 复杂的文件上传逻辑
        video_file = upload_file(str(path.absolute()))
        while video_file.state.name == "PROCESSING":
            time.sleep(2)
            video_file = get_file(video_file.name)
        video = Video(id=video_file.name, url=video_file.uri)
        response = self.agent.run(prompt, videos=[video])
```

#### 修改后 (After)

```python
def analyze(self, video_path: str, video_id: Optional[str] = None):
    # ✅ 统一的简单逻辑
    video = Video(filepath=str(path.absolute()))
    response = self.agent.run(prompt, videos=[video])
```

### 5. 更新的便捷函数

#### 修改前 (Before)

```python
def create_content_analyzer(
    model: str = "gemini/gemini-2.0-flash-exp",
    **kwargs
) -> ContentAnalyzerAgent:
    return ContentAnalyzerAgent(model=model, **kwargs)
```

#### 修改后 (After)

```python
def create_content_analyzer(
    model: str = "qwen-vl-plus",  # ✅ 改为 DashScope 模型
    **kwargs
) -> ContentAnalyzerAgent:
    """
    创建ContentAnalyzerAgent实例

    Args:
        model: DashScope模型名称（默认: qwen-vl-plus）
        **kwargs: 其他参数传递给ContentAnalyzerAgent

    Returns:
        ContentAnalyzerAgent实例
    """
    return ContentAnalyzerAgent(model=model, **kwargs)
```

---

## 📊 代码统计

| 指标 | 修改前 | 修改后 | 变化 |
|------|--------|--------|------|
| 总行数 | 395 | 347 | -48行 (-12%) |
| 导入模块 | 5 | 3 | -2个 |
| 支持的Provider | 2 (Gemini, OpenRouter) | 1 (DashScope) | -1个 |
| analyze 方法行数 | ~100行 | ~50行 | -50行 |
| 视频上传逻辑 | 复杂（重试+等待） | 简单（直接加载） | 简化 |

---

## 💡 使用方式

### 基础使用

```python
from app.agents.content_analyzer import ContentAnalyzerAgent

# 创建 Agent（默认使用 qwen-vl-plus）
analyzer = ContentAnalyzerAgent()

# 分析视频
result = analyzer.analyze("/path/to/video.mp4")

# 访问分析结果
print(f"视频ID: {result.video_id}")
print(f"时长: {result.duration}秒")
print(f"关键时刻: {len(result.key_moments)}个")
```

### 自定义配置

```python
from app.agents.content_analyzer import ContentAnalyzerAgent

# 使用 qwen-vl-max 模型，自定义温度
analyzer = ContentAnalyzerAgent(
    model="qwen-vl-max",
    temperature=0.5,
    api_key="sk-xxxxxxxxxx"  # 可选，默认从环境变量读取
)

# 分析视频
result = analyzer.analyze(
    video_path="/path/to/video.mp4",
    video_id="custom_id"
)
```

### 使用便捷函数

```python
from app.agents.content_analyzer import create_content_analyzer

# 快速创建
analyzer = create_content_analyzer(
    model="qwen-vl-plus",
    temperature=0.3
)

result = analyzer.analyze("/path/to/video.mp4")
```

---

## ⚙️ 环境配置

### 必需的环境变量

```bash
# .env 文件
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
```

### 获取 API 密钥

访问 [DashScope API Keys](https://dashscope.aliyun.com/api-keys) 获取 API 密钥。

### 依赖安装

```bash
pip install agno dashscope
```

---

## 🔄 迁移检查清单

如果你的项目中有其他代码引用了旧的 ContentAnalyzerAgent，请检查：

- [ ] ✅ 移除 `provider` 参数（已不再支持）
- [ ] ✅ 模型名称改为 DashScope 模型（如 `qwen-vl-plus`）
- [ ] ✅ 确保 `DASHSCOPE_API_KEY` 环境变量已配置
- [ ] ✅ 移除任何 Gemini 或 OpenRouter 特定的配置

### 示例迁移

#### 迁移前

```python
# ❌ 旧代码
analyzer = ContentAnalyzerAgent(
    model="gemini-2.0-flash-exp",
    provider="gemini"
)
```

#### 迁移后

```python
# ✅ 新代码
analyzer = ContentAnalyzerAgent(
    model="qwen-vl-plus"
)
```

---

## 🎯 支持的模型

| 模型名称 | 能力 | 推荐场景 |
|---------|------|----------|
| `qwen-vl-plus` | 视觉理解 | 通用视频分析（推荐） |
| `qwen-vl-max` | 更强视觉理解 | 复杂场景分析 |

---

## 🐛 常见问题

### Q1: 导入错误 "No module named 'agno'"

**解决方案**:
```bash
pip install agno dashscope
```

### Q2: API 错误 "Invalid API Key"

**解决方案**:
1. 检查 `.env` 文件中的 `DASHSCOPE_API_KEY` 是否正确
2. 确认 API 密钥以 `sk-` 开头
3. 验证 API 密钥在 DashScope 控制台中是否有效

### Q3: 视频分析失败

**可能原因**:
- 视频文件过大（建议 <50MB）
- 视频格式不支持（推荐 mp4 格式）
- 网络连接问题

**解决方案**:
```python
# 先压缩视频
from app.services.video_preprocessing_service import video_preprocessing_service

compressed_path = await video_preprocessing_service.compress_video(
    video_path="/path/to/large_video.mp4",
    target_size_mb=10
)

# 再分析
result = analyzer.analyze(compressed_path)
```

### Q4: 分析结果不完整

**解决方案**: 增加 temperature 参数以提高创造性

```python
analyzer = ContentAnalyzerAgent(
    model="qwen-vl-max",  # 使用更强大的模型
    temperature=0.5  # 提高温度
)
```

---

## 🔗 相关文档

- [Agno DashScope 集成指南](./AGNO_DASHSCOPE_INTEGRATION.md)
- [DashScope 官方文档](https://help.aliyun.com/zh/dashscope/)
- [Agno 官方文档](https://docs.agno.com/concepts/models/dashscope)

---

## 📞 技术支持

如有问题，请：
1. 查看 [AGNO_DASHSCOPE_INTEGRATION.md](./AGNO_DASHSCOPE_INTEGRATION.md)
2. 运行测试脚本：`python test_simple_dashscope.py`
3. 提交 Issue 到项目仓库

---

**最后更新**: 2025-11-12
**修改人**: Claude Code + Auto-Clip Team
