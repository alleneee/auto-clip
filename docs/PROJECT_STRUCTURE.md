# 项目目录结构说明

## 📁 整体架构

```
auto-clip/
├── app/                        # 应用主目录
│   ├── adapters/              # AI服务适配器层（新增）⭐
│   ├── core/                  # 核心模块
│   ├── services/              # 业务服务层
│   ├── utils/                 # 工具函数层
│   ├── models/                # 数据模型
│   ├── api/                   # API接口
│   ├── workers/               # 后台任务
│   └── prompts/               # AI提示词
├── docs/                      # 项目文档
└── tests/                     # 测试文件
```

## 🏗️ 分层架构

### 1. **Adapters 层** (app/adapters/) ⭐ 新增
**职责**: AI服务适配器，实现依赖倒置原则（DIP）

```
app/adapters/
├── __init__.py                 # 统一导出所有适配器
├── vision_adapters.py          # 视觉分析适配器
├── audio_adapters.py           # 语音识别适配器
├── text_adapters.py            # 文本生成适配器
└── tts_adapters.py             # 文本转语音适配器
```

**设计原则**:
- ✅ 实现 Protocol 接口（IVisionAnalysisService, ISpeechRecognitionService等）
- ✅ 封装第三方AI服务（DashScope, Paraformer等）
- ✅ 便于替换服务提供商

### 2. **Core 层** (app/core/)
**职责**: 核心抽象和基础设施

```
app/core/
├── __init__.py
├── exceptions.py               # 自定义异常
├── middleware.py               # 中间件
├── service_factory.py          # 服务工厂（DI容器）
└── protocols/                  # 协议定义目录 ⭐
    ├── __init__.py
    ├── vision_protocols.py     # 视觉分析协议
    ├── audio_protocols.py      # 语音识别协议
    ├── text_protocols.py       # 文本生成协议
    ├── tts_protocols.py        # TTS协议
    ├── video_protocols.py      # 视频处理协议
    └── storage_protocols.py    # 存储服务协议
```

**设计原则**:
- ✅ 定义抽象接口（Protocol）
- ✅ 管理依赖注入（ServiceFactory）
- ✅ 协议按领域分离

### 3. **Services 层** (app/services/)
**职责**: 业务逻辑编排和服务组合

```
app/services/
├── __init__.py
├── video_analysis_orchestrator.py  # 视频分析编排器（核心）
├── video_content_analyzer.py       # 视频内容分析
├── audio_extractor.py              # 音频提取服务 ⭐
├── video_preprocessor.py           # 视频预处理服务 ⭐
├── video_compression.py            # 视频压缩服务 ⭐
├── video_editing.py                # 视频编辑服务 ⭐
├── video_analyzer.py               # 视频分析器
├── video_service.py                # 视频业务服务
├── task_service.py                 # 任务管理服务
└── temp_storage.py                 # 临时存储服务
```

**重构改进** ⭐:
- ✅ Service层专注业务编排
- ✅ 调用 Utils层工具函数处理底层操作
- ✅ 业务异常转换和验证

### 4. **Utils 层** (app/utils/)
**职责**: 纯函数工具，无业务逻辑

```
app/utils/
├── __init__.py
├── video_utils.py              # 视频处理工具 ⭐ 新增
├── audio_utils.py              # 音频处理工具 ⭐ 新增
├── logger.py                   # 日志工具
├── json_parser.py              # JSON解析工具
├── oss_client.py               # OSS客户端
├── redis_client.py             # Redis客户端
└── ai_clients/                 # AI客户端封装
    ├── dashscope_client.py     # 阿里云DashScope
    └── paraformer_client.py    # Paraformer ASR
```

**重构改进** ⭐:
- ✅ 视频/音频操作抽取为纯函数
- ✅ 使用 MoviePy 统一技术栈
- ✅ 易于单元测试和复用

### 5. **Models 层** (app/models/)
**职责**: 数据模型定义

```
app/models/
├── __init__.py
├── task.py                     # 任务模型
├── video.py                    # 视频模型
├── video_source.py             # 视频源和压缩配置
├── clip_decision.py            # 剪辑决策
├── batch_processing.py         # 批处理模型
└── responses.py                # API响应模型
```

### 6. **API 层** (app/api/)
**职责**: REST API接口

```
app/api/
├── __init__.py
└── v1/
    ├── __init__.py
    ├── videos.py               # 视频相关API
    ├── tasks.py                # 任务相关API
    └── batch.py                # 批处理API
```

### 7. **Workers 层** (app/workers/)
**职责**: 异步后台任务

```
app/workers/
├── __init__.py
├── celery_app.py               # Celery应用配置
└── batch_processing_tasks.py  # 批处理任务
```

## 🔄 数据流向

```
API层
  ↓
Services层（业务编排）
  ↓
Adapters层（第三方服务） + Utils层（工具函数）
  ↓
Models层（数据模型）
```

## 🎯 SOLID 原则体现

### 单一职责原则 (SRP)
- **Adapters**: 只负责适配第三方服务
- **Services**: 只负责业务编排
- **Utils**: 只提供纯函数工具
- **Core/Protocols**: 只定义抽象接口

### 开闭原则 (OCP)
- 新增AI服务提供商：只需添加新的Adapter
- 新增业务功能：扩展Service层，不修改现有代码

### 里氏替换原则 (LSP)
- 所有Adapter实现相同的Protocol接口
- 可以无缝替换服务提供商

### 接口隔离原则 (ISP)
- 按领域分离Protocol（Vision, Audio, Text, TTS, Video, Storage）
- 每个接口职责单一明确

### 依赖倒置原则 (DIP)
- Services依赖Protocol抽象，不依赖具体实现
- 通过ServiceFactory进行依赖注入

## 📊 重构收益

| 维度 | 改进 |
|------|------|
| **代码组织** | ⭐⭐⭐⭐⭐ 目录结构清晰，职责分离 |
| **可维护性** | ⭐⭐⭐⭐⭐ 修改影响范围小 |
| **可测试性** | ⭐⭐⭐⭐⭐ Utils层纯函数易测 |
| **可扩展性** | ⭐⭐⭐⭐ 新增功能只需扩展对应层 |
| **技术栈一致** | ⭐⭐⭐⭐⭐ 统一使用MoviePy |

## 🔧 重构要点

### 已完成 ✅
1. ✅ 创建 `app/adapters/` 目录，分离适配器
2. ✅ 创建 `app/core/protocols/` 目录，分离协议定义
3. ✅ 创建 `app/utils/video_utils.py` 和 `audio_utils.py`
4. ✅ 重构所有Service层使用Utils工具函数
5. ✅ 清理冗余代码和导入
6. ✅ 更新导入路径
7. ✅ 删除向后兼容文件，保持代码清晰

## 📝 使用示例

```python
# 导入适配器
from app.adapters import DashScopeVisionAdapter, ParaformerSpeechAdapter

# 导入协议
from app.core.protocols.vision_protocols import IVisionAnalysisService
from app.core.protocols.audio_protocols import ISpeechRecognitionService

# 导入工具函数
from app.utils.video_utils import get_video_info, extract_video_clip
from app.utils.audio_utils import extract_audio_from_video

# 导入服务
from app.services.video_analysis_orchestrator import VideoAnalysisOrchestrator
```

## 📚 相关文档

- [视频工具重构说明](./VIDEO_UTILS_REFACTORING.md)
- [SOLID原则实践](./SOLID_REFACTORING.md)
