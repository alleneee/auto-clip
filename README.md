# 🎬 Auto-Clip 自动视频剪辑系统

> AI驱动的智能视频剪辑平台，支持多视频导入、自动内容分析和精彩片段提取

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)

## 📋 功能特性

### 🎥 视频导入
- **本地上传**：支持批量上传多个视频文件
- **URL导入**：从直链地址自动下载视频
- **OSS导入**：从阿里云OSS直接导入（待实现）

### 🤖 AI智能分析
- **视觉分析**：基于阿里云DashScope qwen-vl-plus的视频内容理解
- **语音识别**：使用Paraformer进行精准语音转文字
- **两阶段LLM推理**：
  - **Pass 1**：分析视频内容并生成主题
  - **Pass 2**：基于主题智能生成剪辑决策

### ✂️ 自动剪辑
- **智能片段提取**：自动识别精彩时刻
- **多视频拼接**：无缝合并多个片段
- **高质量输出**：H.264编码，保证画质

### ☁️ 存储管理
- **混合存储**：本地缓存 + 阿里云OSS持久化
- **灵活配置**：支持纯本地、纯云端或混合模式

### 🔔 通知系统
- **Webhook回调**：任务完成自动通知
- **任务追踪**：实时查询处理进度

## 🏗️ 架构设计

```
┌─────────┐     ┌──────────────┐     ┌─────────────┐
│  用户   │────▶│  FastAPI     │────▶│   Redis     │
│  上传   │     │  API服务     │     │  任务队列   │
└─────────┘     └──────────────┘     └─────────────┘
                        │                     │
                        ▼                     ▼
                ┌──────────────┐     ┌─────────────┐
                │  存储服务    │     │  Celery     │
                │  本地+OSS    │     │  Workers    │
                └──────────────┘     └─────────────┘
                        │                     │
                        │        ┌────────────┼────────────┐
                        │        ▼            ▼            ▼
                        │   ┌────────┐  ┌─────────┐  ┌─────────┐
                        │   │ 视频   │  │  LLM    │  │ MoviePy │
                        │   │ 分析   │  │ 服务    │  │ 剪辑    │
                        │   └────────┘  └─────────┘  └─────────┘
                        │        │            │            │
                        └────────┴────────────┴────────────┘
                                      │
                                      ▼
                              ┌──────────────┐
                              │  Webhook     │
                              │  通知用户    │
                              └──────────────┘
```

## 🚀 快速开始

### 前置要求

- Python 3.10+
- Docker & Docker Compose（推荐）
- FFmpeg
- 阿里云DashScope API密钥

### 1. 克隆项目

```bash
git clone <repository-url>
cd auto-clip
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入必要的配置：

```env
# DashScope API密钥（必填）
DASHSCOPE_API_KEY=sk-your-api-key-here

# 阿里云OSS配置（可选）
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
OSS_ACCESS_KEY_ID=your_access_key
OSS_ACCESS_KEY_SECRET=your_secret_key
OSS_BUCKET_NAME=auto-clip-videos

# Paraformer配置（可选）
PARAFORMER_APP_KEY=your_app_key
```

### 3. 使用Docker启动（推荐）

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 4. 本地开发模式

```bash
# 安装依赖
pip install -r requirements.txt

# 启动Redis（需要单独安装）
redis-server

# 启动FastAPI服务
python -m app.main

# 启动Celery Worker（另开终端）
celery -A app.workers.celery_app worker -l info
```

## 📖 API文档

启动服务后访问：

- **Swagger UI**：http://localhost:8000/api/v1/docs
- **ReDoc**：http://localhost:8000/api/v1/redoc
- **Flower监控**：http://localhost:5555

### 核心API端点

#### 上传视频
```bash
curl -X POST "http://localhost:8000/api/v1/videos/upload" \
  -F "file=@your_video.mp4"
```

#### URL导入
```bash
curl -X POST "http://localhost:8000/api/v1/videos/import-url" \
  -F "url=https://example.com/video.mp4"
```

#### 创建剪辑任务
```bash
curl -X POST "http://localhost:8000/api/v1/tasks/create" \
  -H "Content-Type: application/json" \
  -d '{
    "video_ids": ["vid_abc123", "vid_def456"],
    "webhook_url": "https://your-webhook.com/callback"
  }'
```

#### 查询任务状态
```bash
curl "http://localhost:8000/api/v1/tasks/{task_id}"
```

## 🔧 配置说明

### 存储模式

在 `.env` 中配置 `STORAGE_BACKEND`：

- `local`：仅本地存储
- `oss`：仅OSS云存储
- `hybrid`：本地缓存 + OSS持久化（推荐）

### 视频处理参数

```env
# 最大文件大小（2GB）
MAX_VIDEO_SIZE=2147483648

# 支持的格式
SUPPORTED_FORMATS=mp4,avi,mov,mkv,flv,wmv

# 并行分析线程数
MAX_PARALLEL_ANALYSIS=4
```

## 🧪 开发指南

### 项目结构

```
auto-clip/
├── app/
│   ├── api/v1/          # API路由
│   ├── models/          # 数据模型
│   ├── services/        # 业务逻辑
│   ├── workers/         # Celery任务
│   ├── utils/           # 工具类
│   └── core/            # 核心模块
├── storage/             # 本地存储
├── tests/               # 测试代码
├── docker-compose.yml   # Docker编排
└── requirements.txt     # Python依赖
```

### 添加新功能

1. 在 `app/models/` 定义数据模型
2. 在 `app/services/` 实现业务逻辑
3. 在 `app/api/v1/` 添加API端点
4. 在 `app/workers/` 创建异步任务（如需要）

### 运行测试

```bash
pytest tests/
```

## 📊 性能指标

- **并发处理**：支持多视频并行分析
- **队列隔离**：分析/剪辑任务分离，避免阻塞
- **资源优化**：分段处理大视频，避免内存溢出
- **智能缓存**：LLM结果缓存，提升响应速度

## 🔍 故障排查

### 常见问题

**1. FFmpeg未找到**
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg
```

**2. Celery Worker未启动**
```bash
# 检查Redis连接
redis-cli ping

# 查看Celery日志
docker-compose logs worker-analyzer
```

**3. DashScope API错误**
```bash
# 验证API密钥
curl -X POST 'https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation' \
  -H "Authorization: Bearer YOUR_API_KEY"
```

## 🛣️ 发展路线

- [x] 基础视频上传和导入
- [x] FFmpeg元数据提取
- [x] DashScope视觉分析集成
- [ ] Paraformer语音识别集成
- [ ] MoviePy剪辑执行
- [ ] 完整Pipeline编排
- [ ] OSS存储集成
- [ ] Webhook通知系统
- [ ] 性能优化和监控
- [ ] 单元测试覆盖

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📧 联系方式

如有问题，请提交Issue或联系维护者。

---

**⚡ Made with FastAPI + DashScope + MoviePy**
