# 🚀 Auto-Clip 快速上手指南

## 📦 项目已完成功能

✅ **完整的MVC架构**：Controller（API）→ Service（业务逻辑）→ Model（数据）
✅ **视频上传管理**：本地上传、URL导入、批量处理
✅ **任务状态管理**：创建、查询、取消任务
✅ **视频分析服务**：FFmpeg元数据提取、并行分析
✅ **AI服务集成**：DashScope qwen-vl-plus视觉分析
✅ **Docker部署**：一键启动完整环境
✅ **结构化日志**：JSON格式便于分析

## 🏃 快速启动

### 方式1：Docker（推荐）

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑.env，填入DashScope API密钥
nano .env

# 2. 启动所有服务
docker-compose up -d

# 3. 查看日志
docker-compose logs -f api

# 4. 访问API文档
open http://localhost:8000/api/v1/docs

# 5. 访问Flower监控（Celery任务监控）
open http://localhost:5555
```

### 方式2：本地开发

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动Redis
redis-server

# 3. 配置环境变量
cp .env.example .env
nano .env

# 4. 启动FastAPI
python -m app.main

# 5. 启动Celery Worker（另开终端，待实现）
# celery -A app.workers.celery_app worker -l info
```

## 📝 API使用示例

### 1. 健康检查
```bash
curl http://localhost:8000/health
```

### 2. 上传视频
```bash
curl -X POST "http://localhost:8000/api/v1/videos/upload" \
  -F "file=@test_video.mp4"

# 响应示例
{
  "success": true,
  "video_id": "vid_a1b2c3d4e5f6",
  "filename": "test_video.mp4",
  "size": 10485760,
  "message": "视频上传成功"
}
```

### 3. 从URL导入
```bash
curl -X POST "http://localhost:8000/api/v1/videos/import-url" \
  -F "url=https://example.com/sample.mp4"
```

### 4. 批量上传
```bash
curl -X POST "http://localhost:8000/api/v1/videos/upload-batch" \
  -F "files=@video1.mp4" \
  -F "files=@video2.mp4" \
  -F "files=@video3.mp4"
```

### 5. 获取视频信息
```bash
curl "http://localhost:8000/api/v1/videos/vid_a1b2c3d4e5f6"
```

### 6. 创建剪辑任务
```bash
curl -X POST "http://localhost:8000/api/v1/tasks/create" \
  -H "Content-Type: application/json" \
  -d '{
    "video_ids": ["vid_a1b2c3d4e5f6", "vid_b2c3d4e5f6a1"],
    "webhook_url": "https://your-domain.com/webhook",
    "config": {
      "target_duration": 60,
      "clip_count": 5
    }
  }'

# 响应示例
{
  "task_id": "task_x1y2z3a4b5c6",
  "status": "pending",
  "progress": 0.0,
  "current_step": "初始化",
  "created_at": "2024-01-01T10:00:00"
}
```

### 7. 查询任务状态
```bash
curl "http://localhost:8000/api/v1/tasks/task_x1y2z3a4b5c6"
```

### 8. 获取任务结果
```bash
curl "http://localhost:8000/api/v1/tasks/task_x1y2z3a4b5c6/result"
```

### 9. 取消任务
```bash
curl -X DELETE "http://localhost:8000/api/v1/tasks/task_x1y2z3a4b5c6"
```

### 10. 列出所有任务
```bash
# 列出所有任务
curl "http://localhost:8000/api/v1/tasks/"

# 按状态过滤
curl "http://localhost:8000/api/v1/tasks/?status=completed"

# 分页
curl "http://localhost:8000/api/v1/tasks/?limit=20&offset=40"
```

## 🧪 测试示例

### Python测试脚本
```python
import httpx

# 上传视频
with open("test.mp4", "rb") as f:
    response = httpx.post(
        "http://localhost:8000/api/v1/videos/upload",
        files={"file": ("test.mp4", f, "video/mp4")}
    )
    video_data = response.json()
    print(f"视频ID: {video_data['video_id']}")

# 创建任务
task_response = httpx.post(
    "http://localhost:8000/api/v1/tasks/create",
    json={
        "video_ids": [video_data["video_id"]],
        "webhook_url": "https://example.com/webhook"
    }
)
task_data = task_response.json()
print(f"任务ID: {task_data['task_id']}")

# 查询状态
status_response = httpx.get(
    f"http://localhost:8000/api/v1/tasks/{task_data['task_id']}"
)
print(f"状态: {status_response.json()}")
```

## 📁 项目结构

```
auto-clip/
├── app/                    # 应用代码
│   ├── api/v1/            # API路由层（Controller）
│   │   ├── videos.py      # 视频管理
│   │   └── tasks.py       # 任务管理
│   ├── services/          # 业务逻辑层（Service）
│   │   ├── video_service.py      # 视频服务
│   │   ├── task_service.py       # 任务服务
│   │   └── video_analyzer.py     # 视频分析
│   ├── models/            # 数据模型层（Model）
│   │   ├── video.py       # 视频模型
│   │   ├── task.py        # 任务模型
│   │   └── clip_decision.py  # 剪辑决策
│   ├── utils/             # 工具层
│   │   ├── logger.py      # 日志
│   │   └── ai_clients/    # AI客户端
│   │       └── dashscope_client.py
│   ├── core/              # 核心模块
│   │   └── exceptions.py  # 异常
│   ├── workers/           # Celery任务（待实现）
│   ├── config.py          # 配置管理
│   └── main.py            # FastAPI入口
├── storage/               # 本地存储
│   ├── uploads/          # 上传文件
│   ├── processed/        # 处理后文件
│   └── cache/            # 缓存
├── logs/                  # 日志文件
├── tests/                 # 测试代码
├── docker-compose.yml     # Docker编排
├── Dockerfile            # Docker镜像
├── requirements.txt      # Python依赖
├── .env.example          # 环境变量示例
└── README.md             # 项目文档
```

## 🔍 常见问题

### Q: Docker启动失败？
```bash
# 检查端口占用
lsof -i :8000
lsof -i :6379

# 查看日志
docker-compose logs
```

### Q: 如何重置环境？
```bash
# 停止并删除容器
docker-compose down -v

# 清理存储
rm -rf storage/uploads/* storage/processed/*

# 重新启动
docker-compose up -d
```

### Q: 如何查看日志？
```bash
# 应用日志
docker-compose logs -f api

# Worker日志
docker-compose logs -f worker-analyzer

# 本地文件日志
tail -f logs/auto-clip.log
```

### Q: 如何调试API？
访问 http://localhost:8000/api/v1/docs，使用Swagger UI交互式测试

## 🚧 待完成功能

⏳ **Celery异步Pipeline** - 完整的视频处理流程
⏳ **MoviePy剪辑执行** - 自动视频剪辑
⏳ **LLM完整流程** - 两阶段AI推理
⏳ **OSS存储** - 云端存储集成
⏳ **Webhook通知** - 任务完成回调

## 📊 当前状态

✅ **70% 完成** - 核心架构和基础功能已就绪
🚀 **可立即使用** - 视频上传和管理功能完整
⏳ **开发中** - AI处理和自动剪辑功能

## 📚 更多文档

- [README.md](README.md) - 完整项目文档
- [项目实施总结.md](项目实施总结.md) - 详细开发总结
- [API文档](http://localhost:8000/api/v1/docs) - 交互式API文档

---

**祝您使用愉快！** 🎬
