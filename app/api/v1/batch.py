"""
批处理 API 端点
多视频批量处理、AI分析和自动剪辑
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any

from app.models.batch_processing import (
    BatchProcessRequest,
    BatchProcessResponse,
    BatchProcessStatus,
    TaskStatusResponse
)
from app.workers import batch_process_videos_task, celery_app
from app.utils.logger import logger

router = APIRouter(prefix="/batch", tags=["Batch Processing"])


@router.post("/process", response_model=BatchProcessResponse)
async def create_batch_process(
    request: BatchProcessRequest,
    background_tasks: BackgroundTasks
) -> BatchProcessResponse:
    """
    创建批处理任务

    提交多个视频进行批量处理：
    1. 下载/准备视频
    2. 压缩视频（降低token成本）
    3. 上传到临时OSS
    4. VL模型并行分析
    5. 文本模型生成剪辑方案
    6. 执行剪辑和拼接
    7. 返回最终视频URL

    Args:
        request: 批处理请求

    Returns:
        BatchProcessResponse: 批处理响应（包含任务ID）
    """
    try:
        logger.info(
            f"接收批处理请求: {len(request.videos)} 个视频, "
            f"策略: {request.clip_strategy}"
        )

        # 验证视频数量
        if len(request.videos) > request.metadata.get('max_videos', 10):
            raise HTTPException(
                status_code=400,
                detail=f"视频数量超过限制: {len(request.videos)} > 10"
            )

        # 准备批处理配置
        batch_config = {
            'global_compression_profile': request.global_compression_profile,
            'temp_storage_expiry_hours': request.temp_storage_expiry_hours,
            'vl_model': request.vl_model,
            'text_model': request.text_model,
            'target_duration': request.target_duration,
            'clip_strategy': request.clip_strategy,
            'output_quality': request.output_quality
        }

        # 转换 VideoSource 对象为字典
        video_sources = [video.model_dump() for video in request.videos]

        # 提交Celery任务
        result = batch_process_videos_task.apply_async(
            args=[video_sources, batch_config]
        )

        task_id = result.id

        logger.info(f"批处理任务已创建: task_id={task_id}")

        # 返回初始响应
        return BatchProcessResponse(
            task_id=task_id,
            status=BatchProcessStatus.PENDING,
            total_videos=len(request.videos),
            processed_videos=0,
            progress_percentage=0
        )

    except Exception as e:
        logger.error(f"创建批处理任务失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"创建批处理任务失败: {str(e)}"
        )


@router.get("/tasks/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(task_id: str) -> TaskStatusResponse:
    """
    查询任务状态

    Args:
        task_id: 任务ID

    Returns:
        TaskStatusResponse: 任务状态信息
    """
    try:
        # 获取Celery任务结果
        result = celery_app.AsyncResult(task_id)

        # 映射Celery状态到BatchProcessStatus
        status_map = {
            'PENDING': BatchProcessStatus.PENDING,
            'STARTED': BatchProcessStatus.PREPARING,
            'RETRY': BatchProcessStatus.PREPARING,
            'SUCCESS': BatchProcessStatus.COMPLETED,
            'FAILURE': BatchProcessStatus.FAILED
        }

        status = status_map.get(result.state, BatchProcessStatus.PENDING)

        # 根据状态确定当前阶段
        stage_map = {
            BatchProcessStatus.PENDING: '等待处理',
            BatchProcessStatus.PREPARING: '准备和压缩视频',
            BatchProcessStatus.ANALYZING: 'AI分析中',
            BatchProcessStatus.PLANNING: '生成剪辑方案',
            BatchProcessStatus.CLIPPING: '剪辑处理中',
            BatchProcessStatus.COMPLETED: '已完成',
            BatchProcessStatus.FAILED: '处理失败'
        }

        current_stage = stage_map.get(status, '处理中')

        # 计算进度（简化版）
        progress_map = {
            BatchProcessStatus.PENDING: 0,
            BatchProcessStatus.PREPARING: 20,
            BatchProcessStatus.ANALYZING: 50,
            BatchProcessStatus.PLANNING: 75,
            BatchProcessStatus.CLIPPING: 90,
            BatchProcessStatus.COMPLETED: 100,
            BatchProcessStatus.FAILED: 0
        }

        progress = progress_map.get(status, 0)

        # 获取错误信息（如果失败）
        error = None
        if result.failed():
            error = str(result.info) if result.info else "任务执行失败"

        return TaskStatusResponse(
            task_id=task_id,
            status=status,
            progress_percentage=progress,
            current_stage=current_stage,
            error=error
        )

    except Exception as e:
        logger.error(f"查询任务状态失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"查询任务状态失败: {str(e)}"
        )


@router.get("/tasks/{task_id}/result", response_model=BatchProcessResponse)
async def get_task_result(task_id: str) -> BatchProcessResponse:
    """
    获取任务完整结果

    Args:
        task_id: 任务ID

    Returns:
        BatchProcessResponse: 完整的批处理结果
    """
    try:
        # 获取Celery任务结果
        result = celery_app.AsyncResult(task_id)

        if not result.ready():
            raise HTTPException(
                status_code=202,
                detail="任务尚未完成，请稍后查询"
            )

        if result.failed():
            error_msg = str(result.info) if result.info else "任务执行失败"
            return BatchProcessResponse(
                task_id=task_id,
                status=BatchProcessStatus.FAILED,
                total_videos=0,
                error=error_msg
            )

        # 获取任务结果
        task_result = result.get()

        # 构建响应（简化版，实际应该从任务元数据中获取更多信息）
        return BatchProcessResponse(
            task_id=task_id,
            status=BatchProcessStatus.COMPLETED,
            total_videos=task_result.get('total_videos', 0),
            processed_videos=task_result.get('processed_videos', 0),
            progress_percentage=100,
            final_video_url=task_result.get('final_video_url'),
            final_video_duration=task_result.get('final_video_duration'),
            final_video_size=task_result.get('final_video_size'),
            total_processing_time=task_result.get('processing_time')
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务结果失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取任务结果失败: {str(e)}"
        )


@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str) -> Dict[str, Any]:
    """
    取消任务

    Args:
        task_id: 任务ID

    Returns:
        Dict: 取消结果
    """
    try:
        result = celery_app.AsyncResult(task_id)

        if result.ready():
            return {
                'success': False,
                'message': '任务已完成，无法取消'
            }

        # 撤销任务
        result.revoke(terminate=True)

        logger.info(f"任务已取消: task_id={task_id}")

        return {
            'success': True,
            'message': '任务已成功取消',
            'task_id': task_id
        }

    except Exception as e:
        logger.error(f"取消任务失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"取消任务失败: {str(e)}"
        )


@router.get("/health")
async def batch_health_check() -> Dict[str, Any]:
    """
    批处理服务健康检查

    Returns:
        Dict: 健康状态
    """
    try:
        # 检查Celery连接
        celery_status = celery_app.control.inspect().active()

        return {
            'status': 'healthy',
            'celery_connected': celery_status is not None,
            'workers_active': len(celery_status) if celery_status else 0
        }

    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return {
            'status': 'unhealthy',
            'error': str(e)
        }
