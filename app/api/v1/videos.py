"""
视频上传和导入API - Controller层
符合MVC架构：仅处理HTTP请求/响应，业务逻辑委托给Service层
"""
from typing import List
from fastapi import APIRouter, File, UploadFile, HTTPException, Form

from app.services.video_service import VideoService
from app.core.exceptions import VideoFormatError, VideoTooLargeError, VideoNotFoundError
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# 初始化服务层
video_service = VideoService()


@router.post("/upload", response_model=dict)
async def upload_video(file: UploadFile = File(...)):
    """
    上传视频文件

    Args:
        file: 上传的文件

    Returns:
        包含video_id和状态的字典
    """
    try:
        # 读取文件内容
        content = await file.read()

        # 调用Service层处理业务逻辑
        result = await video_service.upload_video(content, file.filename)

        return result

    except (VideoFormatError, VideoTooLargeError) as e:
        logger.warning("video_upload_rejected", reason=e.message)
        raise HTTPException(status_code=400, detail=e.message)

    except Exception as e:
        logger.error("video_upload_failed", error=str(e))
        raise HTTPException(status_code=500, detail="视频上传失败")


@router.post("/upload-batch", response_model=dict)
async def upload_videos_batch(files: List[UploadFile] = File(...)):
    """
    批量上传视频文件

    Args:
        files: 上传的文件列表

    Returns:
        上传结果列表
    """
    try:
        # 读取所有文件内容
        file_data = []
        for file in files:
            content = await file.read()
            file_data.append((content, file.filename))

        # 调用Service层批量处理
        result = await video_service.batch_upload(file_data)

        return result

    except Exception as e:
        logger.error("batch_upload_failed", error=str(e))
        raise HTTPException(status_code=500, detail="批量上传失败")


@router.post("/import-url", response_model=dict)
async def import_from_url(url: str = Form(...)):
    """
    从URL导入视频

    Args:
        url: 视频URL地址

    Returns:
        包含video_id的字典
    """
    try:
        # 调用Service层处理导入逻辑
        result = await video_service.import_from_url(url)

        return result

    except (VideoFormatError, VideoTooLargeError) as e:
        logger.warning("video_import_rejected", url=url, reason=e.message)
        raise HTTPException(status_code=400, detail=e.message)

    except Exception as e:
        logger.error("url_import_error", url=url, error=str(e))
        raise HTTPException(status_code=500, detail=f"视频导入失败: {str(e)}")


@router.post("/import-oss", response_model=dict)
async def import_from_oss(oss_path: str = Form(...)):
    """
    从阿里云OSS导入视频

    Args:
        oss_path: OSS对象路径

    Returns:
        包含video_id的字典
    """
    try:
        # 调用Service层处理OSS导入
        result = await video_service.import_from_oss(oss_path)

        return result

    except Exception as e:
        logger.error("oss_import_error", oss_path=oss_path, error=str(e))
        raise HTTPException(status_code=500, detail="OSS导入失败")


@router.get("/{video_id}", response_model=dict)
async def get_video_info(video_id: str):
    """
    获取视频信息

    Args:
        video_id: 视频ID

    Returns:
        视频信息
    """
    try:
        # 调用Service层获取视频信息
        result = video_service.get_video_info(video_id)

        return result

    except VideoNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)

    except Exception as e:
        logger.error("get_video_info_failed", video_id=video_id, error=str(e))
        raise HTTPException(status_code=500, detail="获取视频信息失败")


@router.delete("/{video_id}")
async def delete_video(video_id: str):
    """
    删除视频

    Args:
        video_id: 视频ID

    Returns:
        删除结果
    """
    try:
        # 调用Service层删除视频
        result = video_service.delete_video(video_id)

        return result

    except VideoNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)

    except Exception as e:
        logger.error("delete_video_failed", video_id=video_id, error=str(e))
        raise HTTPException(status_code=500, detail="删除视频失败")
