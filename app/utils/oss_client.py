"""
阿里云OSS客户端
提供文件上传、下载、删除等基础功能
"""
import os
from typing import Optional, Dict, Any, BinaryIO
from datetime import datetime, timedelta
import oss2
from oss2.credentials import EnvironmentVariableCredentialsProvider

from app.config import settings
from app.core.exceptions import StorageError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OSSClient:
    """阿里云OSS客户端封装"""

    def __init__(
        self,
        access_key_id: Optional[str] = None,
        access_key_secret: Optional[str] = None,
        endpoint: Optional[str] = None,
        bucket_name: Optional[str] = None
    ):
        """
        初始化OSS客户端

        Args:
            access_key_id: 阿里云AccessKey ID（可选，默认从配置读取）
            access_key_secret: 阿里云AccessKey Secret（可选，默认从配置读取）
            endpoint: OSS Endpoint（可选，默认从配置读取）
            bucket_name: OSS Bucket名称（可选，默认从配置读取）

        注意：如果使用环境变量凭证，可以不传入access_key参数
        """
        # 配置参数
        self.access_key_id = access_key_id or settings.OSS_ACCESS_KEY_ID
        self.access_key_secret = access_key_secret or settings.OSS_ACCESS_KEY_SECRET
        self.endpoint = endpoint or settings.OSS_ENDPOINT
        self.bucket_name = bucket_name or settings.OSS_BUCKET_NAME

        # 创建认证对象
        if self.access_key_id and self.access_key_secret:
            auth = oss2.Auth(self.access_key_id, self.access_key_secret)
        else:
            # 使用环境变量凭证
            auth = oss2.ProviderAuth(EnvironmentVariableCredentialsProvider())

        # 创建Bucket对象
        try:
            self.bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name)

            # 验证连接（可选）
            # self.bucket.get_bucket_info()

            logger.info(
                "oss_client_initialized",
                endpoint=self.endpoint,
                bucket=self.bucket_name
            )

        except Exception as e:
            logger.error("oss_client_init_failed", error=str(e))
            raise StorageError(f"OSS客户端初始化失败: {str(e)}")

    async def download(
        self,
        oss_path: str,
        local_path: Optional[str] = None
    ) -> bytes:
        """
        从OSS下载文件

        Args:
            oss_path: OSS对象路径（例如: "videos/example.mp4"）
            local_path: 本地保存路径（可选）
                       如果提供，则保存到文件
                       如果不提供，则返回文件内容（bytes）

        Returns:
            bytes: 文件内容（如果未提供local_path）
                   或空bytes（如果保存到文件）

        Raises:
            StorageError: 下载失败时抛出

        示例:
            # 下载到内存
            content = await oss_client.download("videos/test.mp4")

            # 下载到文件
            await oss_client.download("videos/test.mp4", "/tmp/test.mp4")
        """
        try:
            logger.info("downloading_from_oss", oss_path=oss_path, local_path=local_path)

            # 检查对象是否存在
            if not self.bucket.object_exists(oss_path):
                raise StorageError(f"OSS对象不存在: {oss_path}")

            # 下载文件
            if local_path:
                # 确保目录存在
                os.makedirs(os.path.dirname(local_path), exist_ok=True)

                # 下载到本地文件
                result = self.bucket.get_object_to_file(oss_path, local_path)

                # 验证下载
                if not os.path.exists(local_path):
                    raise StorageError(f"文件下载后未找到: {local_path}")

                file_size = os.path.getsize(local_path)

                logger.info(
                    "oss_download_success",
                    oss_path=oss_path,
                    local_path=local_path,
                    file_size_mb=file_size / (1024 * 1024)
                )

                return b''  # 返回空bytes

            else:
                # 下载到内存
                result = self.bucket.get_object(oss_path)
                content = result.read()

                logger.info(
                    "oss_download_success",
                    oss_path=oss_path,
                    content_size_mb=len(content) / (1024 * 1024)
                )

                return content

        except oss2.exceptions.OssError as e:
            error_msg = f"OSS下载失败: {e.code} - {e.message}"
            logger.error("oss_download_failed", oss_path=oss_path, error=error_msg)
            raise StorageError(error_msg)

        except Exception as e:
            error_msg = f"OSS下载失败: {str(e)}"
            logger.error("oss_download_exception", oss_path=oss_path, error=error_msg)
            raise StorageError(error_msg)

    async def upload(
        self,
        local_path: str,
        oss_path: str,
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        上传文件到OSS

        Args:
            local_path: 本地文件路径
            oss_path: OSS对象路径
            content_type: Content-Type（可选，自动检测）

        Returns:
            Dict: 上传结果
                - oss_path: OSS对象路径
                - public_url: 公网访问URL（如果Bucket公开）
                - size: 文件大小

        Raises:
            StorageError: 上传失败时抛出
        """
        try:
            if not os.path.exists(local_path):
                raise StorageError(f"本地文件不存在: {local_path}")

            logger.info("uploading_to_oss", local_path=local_path, oss_path=oss_path)

            # 上传文件
            result = self.bucket.put_object_from_file(
                oss_path,
                local_path,
                headers={'Content-Type': content_type} if content_type else None
            )

            file_size = os.path.getsize(local_path)

            # 生成公网URL（如果Bucket是公开的）
            public_url = f"https://{self.bucket_name}.{self.endpoint}/{oss_path}"

            logger.info(
                "oss_upload_success",
                oss_path=oss_path,
                file_size_mb=file_size / (1024 * 1024)
            )

            return {
                "oss_path": oss_path,
                "public_url": public_url,
                "size": file_size,
                "etag": result.etag if hasattr(result, 'etag') else None
            }

        except Exception as e:
            error_msg = f"OSS上传失败: {str(e)}"
            logger.error("oss_upload_failed", local_path=local_path, error=error_msg)
            raise StorageError(error_msg)

    async def delete(self, oss_path: str) -> bool:
        """
        删除OSS对象

        Args:
            oss_path: OSS对象路径

        Returns:
            bool: 删除是否成功

        Raises:
            StorageError: 删除失败时抛出
        """
        try:
            logger.info("deleting_from_oss", oss_path=oss_path)

            self.bucket.delete_object(oss_path)

            logger.info("oss_delete_success", oss_path=oss_path)

            return True

        except Exception as e:
            error_msg = f"OSS删除失败: {str(e)}"
            logger.error("oss_delete_failed", oss_path=oss_path, error=error_msg)
            raise StorageError(error_msg)

    def generate_signed_url(
        self,
        oss_path: str,
        expires: int = 3600,
        method: str = 'GET'
    ) -> str:
        """
        生成OSS签名URL

        Args:
            oss_path: OSS对象路径
            expires: 过期时间（秒）
            method: HTTP方法（GET/PUT）

        Returns:
            str: 签名URL

        Raises:
            StorageError: 生成失败时抛出
        """
        try:
            url = self.bucket.sign_url(method, oss_path, expires)

            logger.debug(
                "oss_signed_url_generated",
                oss_path=oss_path,
                expires=expires
            )

            return url

        except Exception as e:
            error_msg = f"生成签名URL失败: {str(e)}"
            logger.error("oss_sign_url_failed", oss_path=oss_path, error=error_msg)
            raise StorageError(error_msg)

    def object_exists(self, oss_path: str) -> bool:
        """
        检查OSS对象是否存在

        Args:
            oss_path: OSS对象路径

        Returns:
            bool: 对象是否存在
        """
        try:
            return self.bucket.object_exists(oss_path)
        except Exception as e:
            logger.error("oss_exists_check_failed", oss_path=oss_path, error=str(e))
            return False


# 单例实例（可选）
oss_client = OSSClient()
