# 提示词系统使用示例

## 快速开始

### 1. 初始化系统

```python
from app.prompts import initialize_prompts

# 初始化提示词系统
catalog = initialize_prompts()
# 输出: ✅ 提示词系统已初始化
# 输出: 📊 已注册 1 个提示词模板
```

### 2. 获取提示词

```python
from app.prompts import get_prompt

# 获取增强版片段决策提示词
prompt = get_prompt("clip_decision.enhanced")

# 查看元数据
print(f"名称: {prompt.metadata.name}")
print(f"版本: {prompt.metadata.version}")
print(f"所需参数: {prompt.metadata.parameters}")
```

### 3. 使用病毒钩子推荐

```python
from app.prompts.viral import ViralHooks, VideoStyle

# 为美食视频推荐最佳钩子
recommendation = ViralHooks.recommend_hook(
    style=VideoStyle.FOOD,
    video_content_summary="展示烹饪过程和最终成品"
)

print(f"推荐钩子: {recommendation['hook_type']}")
print(f"成功率: {recommendation['success_rate']}")
print(f"模板: {recommendation['template']}")
print(f"使用场景: {recommendation['use_case']}")
```

输出示例:
```
推荐钩子: 成果展示
成功率: 0.89
模板: 看看最后的成品，简直不敢相信...
使用场景: 美食类，特别适合展示最终成品
```

### 4. 生成情感曲线

```python
from app.prompts.viral import ViralTechniques

# 获取适合60秒视频的情感曲线
emotion_curve = ViralTechniques.get_emotion_curve_by_duration(60)

print(f"曲线类型: {emotion_curve['name']}")
for point in emotion_curve['pattern']:
    print(f"{point['time']}: {point['emotion']} (强度: {point['intensity']})")
```

### 5. 生成片段节奏指南

```python
# 生成60秒视频的节奏指南
rhythm_guide = ViralTechniques.generate_clip_rhythm_guide(60)

print("结构分配:")
print(f"开头: {rhythm_guide['opening']['start']}-{rhythm_guide['opening']['end']}秒")
print(f"  重点: {rhythm_guide['opening']['focus']}")
print(f"高潮: {rhythm_guide['climax']['start']}-{rhythm_guide['climax']['end']}秒")
print(f"  重点: {rhythm_guide['climax']['focus']}")
```

### 6. 完整的片段决策流程

```python
from app.prompts import get_prompt
from app.prompts.viral import ViralHooks, VideoStyle

# 1. 准备视频分析数据
video_analyses = [
    {
        "time": "00:00:05.0",
        "visual": "食材准备，特写镜头",
        "audio": "轻快背景音乐",
        "scene_score": 0.85
    },
    {
        "time": "00:00:30.0",
        "visual": "烹饪过程，炒制动作",
        "audio": "锅铲碰撞声",
        "scene_score": 0.78
    },
    {
        "time": "00:01:15.0",
        "visual": "成品展示，摆盘特写",
        "audio": "舒缓音乐",
        "scene_score": 0.95
    }
]

# 2. 获取钩子推荐
hook_recommendation = ViralHooks.recommend_hook(
    style=VideoStyle.FOOD,
    video_content_summary="美食制作过程"
)

# 3. 获取并格式化提示词
prompt = get_prompt("clip_decision.enhanced")
formatted_prompt = prompt.format_prompt(
    theme="家常美食制作教程",
    video_analyses=video_analyses,
    target_duration=60,
    viral_style="美食",
    recommended_hook=hook_recommendation
)

# 4. 调用AI模型
# response = call_ai_model(formatted_prompt, video_frames)

# 5. 验证输出格式
# is_valid, parsed_data = prompt.validate_output(response)
# if is_valid:
#     clips = parsed_data['clips']
#     viral_strategy = parsed_data['viral_strategy']
```

## 高级用法

### 注册新的提示词

```python
from app.prompts.base import VisionPrompt
from app.prompts.registry import PromptRegistry
from app.prompts.metadata import PromptMetadata, ModelType, OutputFormat

@PromptRegistry.register(category="custom", name="my_prompt")
class MyCustomPrompt(VisionPrompt):
    def __init__(self):
        metadata = PromptMetadata(
            name="my_custom_prompt",
            category="custom",
            version="v1.0",
            model_type=ModelType.VISION,
            output_format=OutputFormat.JSON,
            parameters=["param1", "param2"],
            description="自定义提示词",
            tags=["custom"]
        )
        super().__init__(metadata)
    
    def get_template(self, version=None):
        return "您的提示词模板内容 {param1} {param2}"
```

### 搜索提示词

```python
from app.prompts.registry import PromptRegistry
from app.prompts.metadata import ModelType

# 按类别搜索
prompts = PromptRegistry.search(category="clip_decision")

# 按模型类型搜索
prompts = PromptRegistry.search(model_type=ModelType.VISION)

# 按标签搜索
prompts = PromptRegistry.search(tags=["viral", "video_editing"])

# 按成功率搜索
prompts = PromptRegistry.search(min_success_rate=0.85)
```

### 性能监控

```python
# 更新提示词性能指标
prompt.metadata.update_metrics(
    success=True,
    tokens=1500,
    latency=2.3
)

# 查看统计信息
stats = PromptRegistry.get_statistics()
print(f"总提示词数: {stats['total_prompts']}")
print(f"总调用次数: {stats['total_calls']}")
print(f"平均成功率: {stats['avg_success_rate']}")
```

### 导出提示词目录

```python
# 导出为JSON格式
catalog = PromptRegistry.export_catalog(
    output_path="/path/to/catalog.json"
)
```

## 病毒传播技巧参考

### 可用的钩子类型

1. **悬念式** (success_rate: 0.92) - 适合剧情类、产品揭秘
2. **反转式** (success_rate: 0.88) - 适合观点类、对比类
3. **数字冲击** (success_rate: 0.91) - 适合成果展示、数据类
4. **痛点共鸣** (success_rate: 0.90) - 适合教程类、解决方案类
5. **成果展示** (success_rate: 0.89) - 适合前后对比、成就类
6. **冲突对比** (success_rate: 0.86) - 适合争议话题
7. **问题触发** (success_rate: 0.87) - 适合教育类、知识类
8. **故事钩子** (success_rate: 0.85) - 适合个人经历
9. **权威背书** (success_rate: 0.83) - 适合专业类
10. **好奇缺口** (success_rate: 0.88) - 适合知识类

### 视频风格与推荐钩子

- **美食**: 成果展示、数字冲击、痛点共鸣
- **科技**: 数字冲击、反转式、成果展示
- **教育**: 问题触发、痛点共鸣、悬念式
- **娱乐**: 悬念式、反转式、故事钩子
- **生活**: 痛点共鸣、故事钩子、成果展示
- **旅行**: 悬念式、成果展示、好奇缺口
- **时尚**: 反转式、成果展示、冲突对比
- **健身**: 成果展示、数字冲击、痛点共鸣
- **商业**: 数字冲击、权威背书、成果展示
- **情感**: 故事钩子、痛点共鸣、反转式

## 向后兼容性

旧版API仍然可用:

```python
# 旧版导入方式仍然有效
from app.prompts import (
    VideoAnalysisPrompts,
    ThemeGenerationPrompts,
    ClipDecisionPrompts
)

# 使用旧版提示词
old_prompt = ClipDecisionPrompts.create_clip_decision_prompt(...)
```

## 最佳实践

1. **始终验证参数**: 使用 `metadata.validate_parameters()` 验证输入
2. **监控性能**: 定期调用 `update_metrics()` 更新性能指标
3. **使用推荐系统**: 让 `ViralHooks.recommend_hook()` 自动选择最佳钩子
4. **遵循情感曲线**: 使用 `get_emotion_curve_by_duration()` 设计情感流
5. **验证输出**: 使用 `validate_output()` 确保AI输出格式正确
