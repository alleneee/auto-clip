"""
视频服务层 - 封装视频相关的业务逻辑
"""
import os
import glob
import uuid
from typing import List, Optional, Dict, Any
import httpx

from app.config import settings
from app.models.video import VideoMetadata
from app.core.exceptions import (
    VideoFormatError,
    VideoTooLargeError,
    VideoNotFoundError,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class VideoService:
    """视频业务逻辑服务"""

    def __init__(self):
        """初始化服务"""
        self.uploads_dir = settings.uploads_dir

    def generate_video_id(self) -> str:
        """
        生成唯一的视频ID

        Returns:
            视频ID字符串
        """
        return f"vid_{uuid.uuid4().hex[:12]}"

    def validate_video_file(self, filename: str, file_size: int) -> None:
        """
        验证视频文件格式和大小

        Args:
            filename: 文件名
            file_size: 文件大小（字节）

        Raises:
            VideoFormatError: 格式不支持
            VideoTooLargeError: 文件过大
        """
        # 检查格式
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in settings.SUPPORTED_FORMATS:
            raise VideoFormatError(
                f"不支持的视频格式: {ext}。支持的格式: {', '.join(settings.SUPPORTED_FORMATS)}"
            )

        # 检查大小
        if file_size > settings.MAX_VIDEO_SIZE:
            max_size_mb = settings.MAX_VIDEO_SIZE / (1024 * 1024)
            actual_size_mb = file_size / (1024 * 1024)
            raise VideoTooLargeError(
                f"视频文件过大: {actual_size_mb:.2f}MB，最大允许: {max_size_mb:.2f}MB"
            )

    def save_video_file(
        self, content: bytes, filename: str, video_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        保存视频文件到本地存储

        Args:
            content: 文件内容
            filename: 原始文件名
            video_id: 视频ID（可选，不提供则自动生成）

        Returns:
            包含video_id、file_path等信息的字典

        Raises:
            VideoFormatError: 格式验证失败
            VideoTooLargeError: 文件过大
        """
        # 生成或使用提供的video_id
        if not video_id:
            video_id = self.generate_video_id()

        file_size = len(content)

        # 验证文件
        self.validate_video_file(filename, file_size)

        # 构建保存路径
        ext = filename.rsplit(".", 1)[-1]
        save_filename = f"{video_id}.{ext}"
        file_path = os.path.join(self.uploads_dir, save_filename)

        # 保存文件
        with open(file_path, "wb") as f:
            f.write(content)

        logger.info(
            "video_saved",
            video_id=video_id,
            filename=filename,
            size=file_size,
            path=file_path,
        )

        return {
            "video_id": video_id,
            "filename": filename,
            "size": file_size,
            "path": file_path,
        }

    async def upload_video(self, content: bytes, filename: str) -> Dict[str, Any]:
        """
        处理视频上传业务逻辑

        Args:
            content: 文件内容
            filename: 文件名

        Returns:
            上传结果
        """
        result = self.save_video_file(content, filename)

        return {
            "success": True,
            "video_id": result["video_id"],
            "filename": result["filename"],
            "size": result["size"],
            "message": "视频上传成功",
        }

    async def import_from_url(self, url: str) -> Dict[str, Any]:
        """
        从URL导入视频

        Args:
            url: 视频URL地址

        Returns:
            导入结果

        Raises:
            VideoFormatError: 格式验证失败
            VideoTooLargeError: 文件过大
        """
        video_id = self.generate_video_id()

        logger.info("importing_video_from_url", video_id=video_id, url=url)

        # 下载视频
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.get(url)
            response.raise_for_status()

            content = response.content

            # 从URL提取文件名
            filename = url.split("/")[-1].split("?")[0]
            if "." not in filename:
                filename = f"video_{video_id}.mp4"

            # 保存视频
            result = self.save_video_file(content, filename, video_id)

        logger.info(
            "video_imported_from_url",
            video_id=result["video_id"],
            url=url,
            size=result["size"],
        )

        return {
            "success": True,
            "video_id": result["video_id"],
            "url": url,
            "size": result["size"],
            "message": "视频导入成功",
        }

    async def import_from_oss(self, oss_path: str) -> Dict[str, Any]:
        """
        从阿里云OSS导入视频

        Args:
            oss_path: OSS对象路径

        Returns:
            导入结果
        """
        video_id = self.generate_video_id()

        logger.info("importing_video_from_oss", video_id=video_id, oss_path=oss_path)

        # TODO: 实现OSS下载逻辑
        # from app.utils.oss_client import OSSClient
        # oss = OSSClient()
        # content = await oss.download(oss_path)
        # result = self.save_video_file(content, filename, video_id)

        return {
            "success": True,
            "video_id": video_id,
            "oss_path": oss_path,
            "message": "OSS导入功能待实现",
        }

    def get_video_info(self, video_id: str) -> Dict[str, Any]:
        """
        获取视频信息

        Args:
            video_id: 视频ID

        Returns:
            视频信息

        Raises:
            VideoNotFoundError: 视频不存在
        """
        # 查找视频文件
        pattern = os.path.join(self.uploads_dir, f"{video_id}.*")
        matches = glob.glob(pattern)

        if not matches:
            raise VideoNotFoundError(f"视频不存在: {video_id}")

        file_path = matches[0]
        file_size = os.path.getsize(file_path)
        filename = os.path.basename(file_path)

        return {
            "video_id": video_id,
            "filename": filename,
            "size": file_size,
            "path": file_path,
            "exists": True,
        }

    def delete_video(self, video_id: str) -> Dict[str, Any]:
        """
        删除视频

        Args:
            video_id: 视频ID

        Returns:
            删除结果

        Raises:
            VideoNotFoundError: 视频不存在
        """
        # 查找并删除视频文件
        pattern = os.path.join(self.uploads_dir, f"{video_id}.*")
        matches = glob.glob(pattern)

        if not matches:
            raise VideoNotFoundError(f"视频不存在: {video_id}")

        for file_path in matches:
            os.remove(file_path)
            logger.info("video_deleted", video_id=video_id, path=file_path)

        return {
            "success": True,
            "video_id": video_id,
            "message": "视频已删除",
        }

    async def batch_upload(
        self, files: List[tuple[bytes, str]]
    ) -> Dict[str, Any]:
        """
        批量上传视频

        Args:
            files: (文件内容, 文件名) 元组列表

        Returns:
            批量上传结果
        """
        results = []
        errors = []

        for content, filename in files:
            try:
                result = await self.upload_video(content, filename)
                results.append(result)
            except (VideoFormatError, VideoTooLargeError) as e:
                errors.append({"filename": filename, "error": e.message})

        return {
            "success": len(errors) == 0,
            "uploaded": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors,
        }
