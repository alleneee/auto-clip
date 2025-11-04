# LLM提示词管理模块

## 📋 概述

本模块集中管理Auto-Clip项目中所有大模型（LLM）调用的提示词。通过将提示词从业务代码中分离出来，实现了更好的可维护性、可测试性和灵活性。

## 🎯 设计目标

1. **关注点分离**：提示词管理与业务逻辑解耦
2. **集中管理**：所有提示词统一存放，便于查找和修改
3. **版本控制**：提示词变更历史可追溯
4. **A/B测试**：支持多个版本的提示词对比测试
5. **多语言支持**：便于实现国际化

## 📁 模块结构

```
app/prompts/
├── __init__.py              # 模块导出
├── llm_prompts.py          # 提示词定义
└── README.md               # 使用文档（本文件）
```

## 🔧 使用方法

### 基础用法

```python
from app.prompts import VideoAnalysisPrompts, ThemeGenerationPrompts

# 使用预定义的视频分析提示词
default_prompt = VideoAnalysisPrompts.VISUAL_ANALYSIS_DEFAULT

# 使用详细分析提示词
detailed_prompt = VideoAnalysisPrompts.VISUAL_ANALYSIS_DETAILED

# 生成主题提示词（动态构建）
theme_prompt = ThemeGenerationPrompts.generate_theme_prompt(analyses)
```

### 在AI客户端中使用

```python
from app.prompts import VideoAnalysisPrompts

class DashScopeClient:
    async def analyze_video_visual(self, video_path: str, prompt: Optional[str] = None):
        # 使用默认提示词或自定义提示词
        actual_prompt = prompt or VideoAnalysisPrompts.VISUAL_ANALYSIS_DEFAULT

        messages = [{
            "role": "user",
            "content": [
                {"video": f"file://{video_path}"},
                {"text": actual_prompt}
            ]
        }]

        # 调用API...
```

## 📚 提示词分类

### 1. VideoAnalysisPrompts - 视频分析提示词

用于视频内容的视觉分析。

**可用提示词**：

- `VISUAL_ANALYSIS_DEFAULT`：默认分析提示词（5个维度）
- `VISUAL_ANALYSIS_DETAILED`：深度分析提示词（包含场景、内容、情感、精彩时刻等）
- `VISUAL_ANALYSIS_QUICK`：快速概览提示词（适合批量处理）

**使用场景**：
```python
# 标准分析
prompt = VideoAnalysisPrompts.VISUAL_ANALYSIS_DEFAULT

# 需要详细报告时
prompt = VideoAnalysisPrompts.VISUAL_ANALYSIS_DETAILED

# 快速预览时
prompt = VideoAnalysisPrompts.VISUAL_ANALYSIS_QUICK
```

### 2. ThemeGenerationPrompts - 主题生成提示词

用于基于多个视频分析结果生成统一主题。

**可用方法**：

- `generate_theme_prompt(analyses)`: 动态生成主题提示词
- `THEME_GENERATION_SYSTEM`: 系统角色提示词

**使用场景**：
```python
# 生成主题
theme_prompt = ThemeGenerationPrompts.generate_theme_prompt(video_analyses)
system_prompt = ThemeGenerationPrompts.THEME_GENERATION_SYSTEM

# 调用LLM
response = await llm_client.chat(theme_prompt, system_prompt=system_prompt)
```

### 3. ClipDecisionPrompts - 剪辑决策提示词

用于LLM Pass 2，生成具体的剪辑决策（clip_list.json）。

**可用方法**：

- `generate_clip_decision_prompt(theme, analyses, target_duration)`: 生成剪辑决策提示词
- `CLIP_DECISION_SYSTEM`: 系统角色提示词

**使用场景**：
```python
# 生成剪辑决策
clip_prompt = ClipDecisionPrompts.generate_clip_decision_prompt(
    theme="精彩瞬间合集",
    analyses=video_analyses,
    target_duration=60  # 目标60秒
)

system_prompt = ClipDecisionPrompts.CLIP_DECISION_SYSTEM
response = await llm_client.chat(clip_prompt, system_prompt=system_prompt)
```

### 4. PromptTemplates - 通用提示词模板

提供通用的提示词处理工具。

**可用方法**：

- `wrap_with_format_instruction(content, format_type)`: 添加格式化指令
- `add_context(base_prompt, context)`: 添加上下文信息

**使用场景**：
```python
# 添加JSON格式要求
json_prompt = PromptTemplates.wrap_with_format_instruction(
    base_prompt,
    format_type="json"
)

# 添加上下文
contextual_prompt = PromptTemplates.add_context(
    base_prompt,
    context={"user_preference": "幽默风格", "target_audience": "年轻人"}
)
```

## 🔄 提示词版本管理

### 创建新版本提示词

当需要优化提示词时，建议保留旧版本以便对比：

```python
class VideoAnalysisPrompts:
    # 当前版本（v2）
    VISUAL_ANALYSIS_DEFAULT = """..."""

    # 旧版本（保留用于对比）
    VISUAL_ANALYSIS_DEFAULT_V1 = """..."""
```

### A/B测试

```python
# 随机选择版本进行测试
import random

def get_analysis_prompt(use_new_version: bool = None):
    if use_new_version is None:
        use_new_version = random.random() > 0.5

    return (VideoAnalysisPrompts.VISUAL_ANALYSIS_DEFAULT
            if use_new_version
            else VideoAnalysisPrompts.VISUAL_ANALYSIS_DEFAULT_V1)
```

## 📊 最佳实践

### 1. 提示词命名规范

- 使用全大写加下划线：`VISUAL_ANALYSIS_DEFAULT`
- 包含用途和类型：`{用途}_{类型}_{版本}`
- 动态生成方法使用动词开头：`generate_theme_prompt()`

### 2. 提示词结构

建议包含以下部分：

```
【角色定义】（可选，作为system prompt）
你是一位...

【任务描述】
请...

【输入数据】
{动态内容}

【输出要求】
1. 格式要求
2. 质量标准
3. 长度限制

【输出格式】（针对结构化输出）
{JSON/Markdown模板}
```

### 3. 动态提示词生成

对于需要根据输入动态构建的提示词，使用静态方法：

```python
@staticmethod
def generate_custom_prompt(data: Dict[str, Any]) -> str:
    """生成自定义提示词"""
    # 构建逻辑
    return prompt
```

### 4. 文档化

每个提示词类和方法都应包含清晰的文档字符串：

```python
class NewPrompts:
    """新功能提示词集合"""

    # 提示词说明
    DEFAULT_PROMPT = """
    用途：...
    适用场景：...
    注意事项：...
    """
```

## 🧪 测试提示词

### 单元测试示例

```python
# tests/test_prompts.py
from app.prompts import VideoAnalysisPrompts, ThemeGenerationPrompts

def test_video_analysis_prompts_exist():
    """测试提示词是否存在"""
    assert VideoAnalysisPrompts.VISUAL_ANALYSIS_DEFAULT
    assert len(VideoAnalysisPrompts.VISUAL_ANALYSIS_DEFAULT) > 0

def test_theme_generation():
    """测试主题生成提示词"""
    analyses = [
        {"visual_analysis": "测试1", "transcript": "语音1"},
        {"visual_analysis": "测试2", "transcript": "语音2"}
    ]

    prompt = ThemeGenerationPrompts.generate_theme_prompt(analyses)

    assert "测试1" in prompt
    assert "测试2" in prompt
    assert "主题" in prompt
```

## 📈 性能考虑

### 提示词长度

- **短提示词** (<100 tokens): 适合简单任务，响应快
- **中等提示词** (100-500 tokens): 平衡质量和速度
- **长提示词** (>500 tokens): 复杂任务，注意成本

### Token使用优化

```python
# ✅ 推荐：清晰简洁
GOOD_PROMPT = """分析视频的：1.场景 2.人物 3.情感"""

# ❌ 避免：冗余啰嗦
BAD_PROMPT = """请你仔细认真地分析一下这个视频里面的各种各样的内容..."""
```

## 🔐 安全注意事项

1. **敏感信息**：不要在提示词中硬编码API密钥、用户数据等敏感信息
2. **注入攻击**：动态构建时注意防止提示词注入攻击
3. **内容审查**：确保提示词符合平台内容政策

```python
# ❌ 不安全
def bad_prompt(user_input: str):
    return f"请分析：{user_input}"  # 用户输入未经验证

# ✅ 安全
def safe_prompt(user_input: str):
    # 验证和清理用户输入
    cleaned = sanitize_input(user_input)
    return f"请分析：{cleaned}"
```

## 🌐 国际化支持

### 多语言提示词

```python
class VideoAnalysisPrompts:
    # 中文版本
    VISUAL_ANALYSIS_ZH = """请分析视频内容..."""

    # 英文版本
    VISUAL_ANALYSIS_EN = """Please analyze the video content..."""

    @staticmethod
    def get_prompt(language: str = "zh"):
        """根据语言获取提示词"""
        prompts = {
            "zh": VideoAnalysisPrompts.VISUAL_ANALYSIS_ZH,
            "en": VideoAnalysisPrompts.VISUAL_ANALYSIS_EN
        }
        return prompts.get(language, VideoAnalysisPrompts.VISUAL_ANALYSIS_ZH)
```

## 📝 变更日志

### v1.0.0 (2024-01-01)
- ✨ 初始版本
- ✨ 添加视频分析提示词（默认、详细、快速）
- ✨ 添加主题生成提示词
- ✨ 添加剪辑决策提示词
- ✨ 添加通用模板工具

## 🤝 贡献指南

添加新提示词时：

1. 在`llm_prompts.py`中添加提示词定义
2. 更新`__init__.py`导出列表
3. 在本文档中添加使用说明
4. 编写单元测试
5. 提交PR并说明用途

## 📞 联系方式

如有问题或建议，请：
- 提交Issue到项目仓库
- 查看项目文档：README.md
- 联系开发团队

---

**提示词即代码** - 将提示词视为代码一样管理，使用版本控制、测试和文档化。
