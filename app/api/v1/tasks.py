"""
任务管理API - Controller层
符合MVC架构：仅处理HTTP请求/响应，业务逻辑委托给Service层
"""
from typing import Optional
from fastapi import APIRouter, HTTPException

from app.models.task import TaskStatus, TaskCreateRequest, TaskResponse
from app.services.task_service import TaskService
from app.core.exceptions import TaskNotFoundError
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# 初始化服务层
task_service = TaskService()


@router.post("/create", response_model=TaskResponse)
async def create_task(request: TaskCreateRequest):
    """
    创建处理任务

    Args:
        request: 任务创建请求

    Returns:
        任务响应
    """
    try:
        # 调用Service层创建任务
        task = task_service.create_task(request)

        return TaskResponse(
            task_id=task.task_id,
            status=task.status,
            progress=task.progress,
            current_step=task.current_step,
            created_at=task.created_at,
        )

    except Exception as e:
        logger.error("task_creation_failed", error=str(e))
        raise HTTPException(status_code=500, detail="任务创建失败")


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: str):
    """
    查询任务状态

    Args:
        task_id: 任务ID

    Returns:
        任务状态
    """
    try:
        # 调用Service层获取任务
        task = task_service.get_task(task_id)

        return TaskResponse(
            task_id=task.task_id,
            status=task.status,
            progress=task.progress,
            current_step=task.current_step,
            result_url=task.result_url,
            created_at=task.created_at,
        )

    except TaskNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)

    except Exception as e:
        logger.error("get_task_status_failed", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail="查询任务状态失败")


@router.get("/{task_id}/result")
async def get_task_result(task_id: str):
    """
    获取任务结果

    Args:
        task_id: 任务ID

    Returns:
        任务完整信息和结果
    """
    try:
        # 调用Service层获取任务结果
        result = task_service.get_task_result(task_id)

        return result

    except TaskNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)

    except Exception as e:
        logger.error("get_task_result_failed", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail="获取任务结果失败")


@router.delete("/{task_id}")
async def cancel_task(task_id: str):
    """
    取消任务

    Args:
        task_id: 任务ID

    Returns:
        取消结果
    """
    try:
        # 调用Service层取消任务
        result = task_service.cancel_task(task_id)

        return result

    except TaskNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)

    except Exception as e:
        logger.error("cancel_task_failed", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail="取消任务失败")


@router.get("/")
async def list_tasks(
    status: Optional[TaskStatus] = None,
    limit: int = 50,
    offset: int = 0,
):
    """
    列出任务

    Args:
        status: 过滤状态
        limit: 返回数量
        offset: 偏移量

    Returns:
        任务列表
    """
    try:
        # 调用Service层获取任务列表
        result = task_service.list_tasks(status, limit, offset)

        return result

    except Exception as e:
        logger.error("list_tasks_failed", error=str(e))
        raise HTTPException(status_code=500, detail="获取任务列表失败")
