# 任务存储配置说明

## 概述

Auto-Clip支持两种任务存储模式：
- **Redis存储**（推荐）：持久化存储，支持分布式部署
- **内存存储**：轻量级存储，适合开发和测试环境

## 配置方式

在`.env`文件中设置`USE_REDIS_FOR_TASKS`参数：

```bash
# 使用Redis存储（推荐用于生产环境）
USE_REDIS_FOR_TASKS=true

# 使用内存存储（推荐用于开发测试）
USE_REDIS_FOR_TASKS=false
```

## 存储模式对比

| 特性 | Redis存储 | 内存存储 |
|------|----------|---------|
| 数据持久化 | ✅ 持久化到磁盘 | ❌ 服务重启丢失 |
| 分布式支持 | ✅ 支持多实例 | ❌ 单实例限制 |
| 性能 | 优秀（网络延迟） | 极快（内存访问） |
| 资源消耗 | 需要Redis服务 | 仅占用应用内存 |
| 适用场景 | 生产环境 | 开发测试环境 |
| 任务TTL | ✅ 7天自动过期 | ❌ 无自动清理 |

## 使用场景

### Redis存储（推荐生产环境）

**何时使用**：
- 生产环境部署
- 需要任务持久化（服务重启不丢失）
- 多实例负载均衡部署
- 需要跨服务共享任务状态

**配置要求**：
```bash
# .env 配置
USE_REDIS_FOR_TASKS=true
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

**优势**：
- ✅ 服务重启后任务状态保留
- ✅ 支持水平扩展（多实例）
- ✅ 自动清理过期任务（7天TTL）
- ✅ 支持分布式架构

**注意事项**：
- 需要运行Redis服务
- 网络延迟影响性能（通常可忽略）

### 内存存储（推荐开发测试）

**何时使用**：
- 本地开发环境
- 单元测试和集成测试
- 不需要任务持久化
- 快速原型验证

**配置要求**：
```bash
# .env 配置
USE_REDIS_FOR_TASKS=false
```

**优势**：
- ✅ 零外部依赖（无需Redis）
- ✅ 极快的读写性能
- ✅ 简化开发环境配置
- ✅ 适合快速迭代开发

**注意事项**：
- ⚠️ 服务重启后任务数据丢失
- ⚠️ 不支持多实例部署
- ⚠️ 内存占用随任务数增长
- ⚠️ 无自动清理机制

## 切换存储模式

### 从内存切换到Redis

1. 确保Redis服务运行：
```bash
# 启动Redis
redis-server

# 验证连接
redis-cli ping
```

2. 更新配置：
```bash
# .env
USE_REDIS_FOR_TASKS=true
```

3. 重启服务：
```bash
# 重启FastAPI应用
pkill -f uvicorn
uvicorn app.main:app --reload
```

**注意**：内存中的任务数据将丢失，需要重新创建任务。

### 从Redis切换到内存

1. 更新配置：
```bash
# .env
USE_REDIS_FOR_TASKS=false
```

2. 重启服务：
```bash
uvicorn app.main:app --reload
```

**注意**：Redis中的任务数据不会丢失，但应用将不再读取Redis数据。

## 性能对比

### Redis存储性能

```
创建任务: ~2-5ms
查询任务: ~1-3ms
列出任务: ~10-50ms (取决于任务数量)
更新任务: ~2-5ms
```

### 内存存储性能

```
创建任务: ~0.1-0.5ms
查询任务: ~0.05-0.2ms
列出任务: ~0.5-2ms (取决于任务数量)
更新任务: ~0.1-0.5ms
```

## 最佳实践

### 生产环境

```bash
# .env 生产配置
USE_REDIS_FOR_TASKS=true
REDIS_HOST=redis-cluster.internal
REDIS_PORT=6379
REDIS_DB=0

# 使用Redis集群提高可用性
# 配置主从复制和哨兵模式
```

### 开发环境

```bash
# .env 开发配置
USE_REDIS_FOR_TASKS=false

# 或者使用本地Redis（如果已安装）
USE_REDIS_FOR_TASKS=true
REDIS_HOST=localhost
REDIS_PORT=6379
```

### 测试环境

```bash
# pytest.ini 或 conftest.py
# 强制使用内存存储进行测试
import os
os.environ['USE_REDIS_FOR_TASKS'] = 'false'
```

## 故障排除

### Redis连接失败

如果使用Redis模式但连接失败：

1. 检查Redis是否运行：
```bash
redis-cli ping
# 应返回: PONG
```

2. 检查配置：
```bash
# 确认.env中Redis配置正确
cat .env | grep REDIS
```

3. 临时切换到内存模式：
```bash
# 快速恢复服务
export USE_REDIS_FOR_TASKS=false
uvicorn app.main:app --reload
```

### 内存占用过高

如果内存模式下内存占用过高：

1. 切换到Redis模式（自动TTL清理）：
```bash
USE_REDIS_FOR_TASKS=true
```

2. 或手动清理旧任务（如果继续使用内存模式）

## 监控和日志

应用启动时会记录当前存储模式：

```
INFO task_service_initialized storage_mode=redis
```

或

```
INFO task_service_initialized storage_mode=memory
```

查看当前存储模式：
```bash
# 查看应用日志
tail -f logs/app.log | grep task_service_initialized
```

## 常见问题

### Q: 可以在运行时切换存储模式吗？

A: 不可以。存储模式在应用启动时确定，需要重启服务才能切换。

### Q: 两种模式的API接口是否一致？

A: 是的。无论使用哪种存储模式，API接口和行为完全一致。

### Q: Redis模式下任务数据保存多久？

A: 默认7天（`task_ttl = 7 * 24 * 3600`秒）。可在`task_service.py`中修改。

### Q: 内存模式下任务数量有限制吗？

A: 仅受可用内存限制。建议生产环境使用Redis模式以避免内存溢出。

### Q: 可以同时使用两种模式吗？

A: 不可以。每个应用实例只能使用一种存储模式。

## 迁移指南

### 从内存迁移到Redis（数据迁移）

如果需要保留内存中的任务数据到Redis：

```python
# 迁移脚本示例
from app.services.task_service import TaskService
from app.utils.redis_client import redis_client

async def migrate_to_redis(memory_tasks):
    """迁移内存任务到Redis"""
    for task_id, task in memory_tasks.items():
        await redis_client.set_task(
            task_id=task_id,
            task_data=task.model_dump(),
            ttl=7 * 24 * 3600
        )
```

**注意**：通常不需要迁移，建议直接切换并重新创建任务。

## 技术实现

核心实现位于 `app/services/task_service.py`：

```python
class TaskService:
    def __init__(self):
        self.use_redis = settings.USE_REDIS_FOR_TASKS
        self.redis = redis_client if self.use_redis else None
        self.memory_storage: Dict[str, Task] = {}

    async def create_task(self, request):
        # ...
        if self.use_redis:
            await self.redis.set_task(task_id, task_data, ttl)
        else:
            self.memory_storage[task_id] = task
```

所有任务操作方法都支持双模式：
- `create_task()`
- `get_task()`
- `list_tasks()`
- `update_task_status()`
- `cancel_task()`

## 总结

- **生产环境**: 强烈推荐使用 `USE_REDIS_FOR_TASKS=true`
- **开发测试**: 可使用 `USE_REDIS_FOR_TASKS=false` 简化配置
- **性能**: 两种模式性能都很好，Redis模式略慢但差异可忽略
- **可靠性**: Redis模式提供数据持久化和分布式支持
- **切换**: 只需修改环境变量并重启服务
