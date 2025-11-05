"""
Celery Workers 模块
异步任务处理
"""
from .celery_app import celery_app
from .batch_processing_tasks import (
    prepare_video_task,
    compress_and_upload_task,
    analyze_video_task,
    generate_clip_plan_task,
    execute_clip_plan_task,
    batch_process_videos_task
)

__all__ = [
    'celery_app',
    'prepare_video_task',
    'compress_and_upload_task',
    'analyze_video_task',
    'generate_clip_plan_task',
    'execute_clip_plan_task',
    'batch_process_videos_task',
]
