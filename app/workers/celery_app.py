"""
Celery 应用配置
批处理任务的分布式队列系统
"""
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure

from app.config import settings
from app.utils.logger import logger

# 创建 Celery 应用实例
celery_app = Celery(
    'auto_clip',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        'app.workers.batch_processing_tasks',
    ]
)

# Celery 配置
celery_app.conf.update(
    # 任务序列化
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,

    # 任务执行配置
    task_track_started=True,
    task_time_limit=settings.TASK_TIMEOUT,  # 任务硬超时
    task_soft_time_limit=settings.TASK_TIMEOUT - 60,  # 任务软超时（提前60秒）

    # 结果后端配置
    result_expires=3600,  # 结果保留1小时
    result_backend_transport_options={
        'master_name': 'mymaster',
        'visibility_timeout': 3600,
    },

    # Worker 配置
    worker_prefetch_multiplier=1,  # 每次只取1个任务（适合长时间任务）
    worker_max_tasks_per_child=50,  # 每个 worker 执行50个任务后重启（防止内存泄漏）
    worker_disable_rate_limits=True,

    # 任务路由（可选）
    task_routes={
        'app.workers.batch_processing_tasks.*': {'queue': 'batch_processing'},
    },

    # 并发配置
    worker_concurrency=settings.BATCH_PARALLEL_LIMIT,
)


# Celery 信号处理器

@task_prerun.connect
def task_prerun_handler(task_id, task, *args, **kwargs):
    """任务开始前的钩子"""
    logger.info(f"任务开始: {task.name} [ID: {task_id}]")


@task_postrun.connect
def task_postrun_handler(task_id, task, *args, **kwargs):
    """任务完成后的钩子"""
    logger.info(f"任务完成: {task.name} [ID: {task_id}]")


@task_failure.connect
def task_failure_handler(task_id, exception, *args, **kwargs):
    """任务失败的钩子"""
    logger.error(
        f"任务失败: [ID: {task_id}]\n"
        f"  异常: {type(exception).__name__}: {str(exception)}",
        exc_info=True
    )


if __name__ == '__main__':
    celery_app.start()
