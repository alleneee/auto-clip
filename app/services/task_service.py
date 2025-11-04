"""
任务服务层 - 封装任务相关的业务逻辑
"""
import uuid
from typing import Optional, Dict, Any

from app.models.task import Task, TaskStatus, TaskCreateRequest
from app.core.exceptions import TaskNotFoundError
from app.utils.logger import get_logger
from app.utils.redis_client import redis_client

logger = get_logger(__name__)


class TaskService:
    """任务业务逻辑服务（使用Redis存储）"""

    def __init__(self):
        """
        初始化服务

        使用Redis作为任务存储后端
        """
        self.redis = redis_client
        # 任务默认TTL（7天）
        self.task_ttl = 7 * 24 * 3600

    def generate_task_id(self) -> str:
        """
        生成唯一的任务ID

        Returns:
            任务ID字符串
        """
        return f"task_{uuid.uuid4().hex[:12]}"

    async def create_task(self, request: TaskCreateRequest) -> Task:
        """
        创建新任务

        Args:
            request: 任务创建请求

        Returns:
            创建的任务对象
        """
        # 生成任务ID
        task_id = self.generate_task_id()

        # 创建任务对象
        task = Task(
            task_id=task_id,
            status=TaskStatus.PENDING,
            video_ids=request.video_ids,
            metadata={
                "webhook_url": request.webhook_url,
                "config": request.config,
            },
        )

        # 存储任务到Redis
        await self.redis.set_task(
            task_id=task_id,
            task_data=task.model_dump(),
            ttl=self.task_ttl
        )

        logger.info(
            "task_created",
            task_id=task_id,
            video_count=len(request.video_ids),
            webhook_url=request.webhook_url,
        )

        # 触发Celery异步处理
        try:
            from app.workers.batch_processing_tasks import process_video_pipeline_task

            # 异步提交任务到Celery
            celery_result = process_video_pipeline_task.delay(
                task_id=task_id,
                video_ids=request.video_ids,
                config=request.config or {}
            )

            # 记录Celery任务ID并更新到Redis
            task.celery_task_id = celery_result.id
            await self.redis.set_task(
                task_id=task_id,
                task_data=task.model_dump(),
                ttl=self.task_ttl
            )

            logger.info(
                "celery_task_submitted",
                task_id=task_id,
                celery_task_id=celery_result.id
            )

        except Exception as e:
            logger.error(
                "celery_task_submit_failed",
                task_id=task_id,
                error=str(e)
            )
            # 即使Celery提交失败，也返回任务对象
            # 任务状态会保持为PENDING

        return task

    async def get_task(self, task_id: str) -> Task:
        """
        获取任务对象

        Args:
            task_id: 任务ID

        Returns:
            任务对象

        Raises:
            TaskNotFoundError: 任务不存在
        """
        task_data = await self.redis.get_task(task_id)

        if not task_data:
            raise TaskNotFoundError(f"任务不存在: {task_id}")

        # 从字典创建Task对象
        task = Task(**task_data)

        return task

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务状态信息

        Args:
            task_id: 任务ID

        Returns:
            任务状态字典

        Raises:
            TaskNotFoundError: 任务不存在
        """
        task = await self.get_task(task_id)

        return {
            "task_id": task.task_id,
            "status": task.status.value,
            "progress": task.progress,
            "current_step": task.current_step,
            "result_url": task.result_url,
            "created_at": task.created_at.isoformat(),
        }

    async def get_task_result(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务结果

        Args:
            task_id: 任务ID

        Returns:
            任务完整信息和结果

        Raises:
            TaskNotFoundError: 任务不存在
        """
        task = await self.get_task(task_id)

        if task.status != TaskStatus.COMPLETED:
            return {
                "task_id": task.task_id,
                "status": task.status.value,
                "progress": task.progress,
                "message": "任务尚未完成",
            }

        return {
            "task_id": task.task_id,
            "status": task.status.value,
            "progress": task.progress,
            "result_url": task.result_url,
            "video_ids": task.video_ids,
            "created_at": task.created_at.isoformat(),
            "completed_at": task.completed_at.isoformat()
            if task.completed_at
            else None,
            "metadata": task.metadata,
        }

    async def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """
        取消任务

        Args:
            task_id: 任务ID

        Returns:
            取消结果

        Raises:
            TaskNotFoundError: 任务不存在
        """
        task = await self.get_task(task_id)

        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            return {
                "success": False,
                "message": "任务已完成或失败，无法取消",
            }

        # 取消Celery任务
        celery_revoked = False
        if hasattr(task, 'celery_task_id') and task.celery_task_id:
            try:
                from app.workers.celery_app import celery_app

                # 撤销Celery任务（terminate=True 强制终止正在执行的任务）
                celery_app.control.revoke(
                    task.celery_task_id,
                    terminate=True,
                    signal='SIGTERM'
                )

                celery_revoked = True

                logger.info(
                    "celery_task_revoked",
                    task_id=task_id,
                    celery_task_id=task.celery_task_id
                )

            except Exception as e:
                logger.error(
                    "celery_task_revoke_failed",
                    task_id=task_id,
                    celery_task_id=task.celery_task_id,
                    error=str(e)
                )

        # 更新任务状态并保存到Redis
        task.status = TaskStatus.CANCELLED
        await self.redis.set_task(
            task_id=task_id,
            task_data=task.model_dump(),
            ttl=self.task_ttl
        )

        logger.info("task_cancelled", task_id=task_id, celery_revoked=celery_revoked)

        return {
            "success": True,
            "task_id": task_id,
            "message": "任务已取消",
            "celery_revoked": celery_revoked,
        }

    async def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        列出任务

        Args:
            status: 过滤状态（可选）
            limit: 返回数量
            offset: 偏移量

        Returns:
            任务列表和分页信息
        """
        # 从Redis获取所有任务ID
        task_ids = await self.redis.list_tasks()

        # 获取所有任务数据
        tasks = []
        for task_id in task_ids:
            task_data = await self.redis.get_task(task_id)
            if task_data:
                tasks.append(Task(**task_data))

        # 状态过滤
        if status:
            tasks = [t for t in tasks if t.status == status]

        # 排序（最新的在前）
        tasks.sort(key=lambda x: x.created_at, reverse=True)

        # 分页
        total = len(tasks)
        tasks = tasks[offset : offset + limit]

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "tasks": [
                {
                    "task_id": t.task_id,
                    "status": t.status.value,
                    "progress": t.progress,
                    "current_step": t.current_step,
                    "created_at": t.created_at.isoformat(),
                }
                for t in tasks
            ],
        }

    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        progress: Optional[float] = None,
        current_step: Optional[str] = None,
        result_url: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Task:
        """
        更新任务状态（供Worker调用）

        Args:
            task_id: 任务ID
            status: 新状态
            progress: 进度（可选）
            current_step: 当前步骤（可选）
            result_url: 结果URL（可选）
            error_message: 错误信息（可选）

        Returns:
            更新后的任务对象

        Raises:
            TaskNotFoundError: 任务不存在
        """
        task = await self.get_task(task_id)

        # 更新状态
        task.update_status(status, progress, current_step)

        # 更新结果URL
        if result_url:
            task.result_url = result_url

        # 设置错误信息
        if error_message:
            task.set_error(error_message)

        # 保存更新到Redis
        await self.redis.set_task(
            task_id=task_id,
            task_data=task.model_dump(),
            ttl=self.task_ttl
        )

        logger.info(
            "task_status_updated",
            task_id=task_id,
            status=status.value,
            progress=progress,
        )

        return task
