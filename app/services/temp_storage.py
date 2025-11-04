"""
临时存储服务
管理临时文件的 OSS 上传、签名 URL 生成和自动清理
"""
import os
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from pathlib import Path

import oss2
from oss2.models import SignedUrlRequest

from app.config import settings
from app.utils.logger import logger


class TempStorageService:
    """临时存储服务"""

    def __init__(self):
        """初始化 OSS 客户端"""
        if not all([
            settings.OSS_ACCESS_KEY_ID,
            settings.OSS_ACCESS_KEY_SECRET,
            settings.OSS_BUCKET_NAME,
            settings.OSS_ENDPOINT
        ]):
            logger.warning("OSS 配置不完整，临时存储服务将无法使用")
            self.bucket = None
            return

        # 创建 OSS 认证和 Bucket 实例
        auth = oss2.Auth(
            settings.OSS_ACCESS_KEY_ID,
            settings.OSS_ACCESS_KEY_SECRET
        )

        self.bucket = oss2.Bucket(
            auth,
            settings.OSS_ENDPOINT,
            settings.OSS_BUCKET_NAME
        )

        # 临时文件前缀
        self.temp_prefix = "temp/"

    def _check_bucket(self):
        """检查 bucket 是否已初始化"""
        if self.bucket is None:
            raise RuntimeError("OSS 未配置，无法使用临时存储服务")

    def generate_temp_key(
        self,
        original_filename: str,
        prefix: str = "compressed"
    ) -> str:
        """
        生成临时文件的 OSS key

        Args:
            original_filename: 原始文件名
            prefix: 文件前缀（如 'compressed', 'downloaded'）

        Returns:
            str: OSS key (例如: temp/compressed/20241104/abc123_video.mp4)
        """
        # 生成时间戳和哈希
        timestamp = datetime.now().strftime("%Y%m%d")
        hash_value = hashlib.md5(
            f"{original_filename}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:8]

        # 提取文件扩展名
        file_ext = Path(original_filename).suffix

        # 构建 key: temp/{prefix}/{date}/{hash}_{filename}
        filename = f"{hash_value}_{Path(original_filename).stem}{file_ext}"
        return f"{self.temp_prefix}{prefix}/{timestamp}/{filename}"

    async def upload_temp_file(
        self,
        local_path: str,
        prefix: str = "compressed",
        expiry_hours: Optional[int] = None
    ) -> Dict[str, str]:
        """
        上传文件到临时存储

        Args:
            local_path: 本地文件路径
            prefix: 文件前缀
            expiry_hours: 过期时间（小时），None 使用默认配置

        Returns:
            Dict: {
                'oss_key': OSS对象key,
                'signed_url': 签名URL,
                'public_url': 公网URL (如果bucket公开),
                'expiry_time': 过期时间ISO格式
            }

        Raises:
            FileNotFoundError: 本地文件不存在
            RuntimeError: OSS 未配置或上传失败
        """
        self._check_bucket()

        if not os.path.exists(local_path):
            raise FileNotFoundError(f"本地文件不存在: {local_path}")

        # 生成 OSS key
        oss_key = self.generate_temp_key(
            os.path.basename(local_path),
            prefix
        )

        # 设置过期时间
        expiry_hours = expiry_hours or settings.TEMP_STORAGE_EXPIRY_HOURS
        expiry_time = datetime.now() + timedelta(hours=expiry_hours)

        try:
            # 上传文件到 OSS
            logger.info(f"开始上传临时文件: {local_path} → {oss_key}")

            with open(local_path, 'rb') as f:
                # 设置对象元数据（包含过期时间）
                headers = {
                    'x-oss-meta-expiry-time': expiry_time.isoformat(),
                    'x-oss-meta-original-name': os.path.basename(local_path),
                    'x-oss-meta-upload-time': datetime.now().isoformat()
                }

                result = self.bucket.put_object(
                    oss_key,
                    f,
                    headers=headers
                )

            if result.status != 200:
                raise RuntimeError(f"OSS 上传失败: {result.status}")

            # 生成签名 URL（用于临时访问）
            signed_url = self.generate_signed_url(
                oss_key,
                expiry_seconds=int(expiry_hours * 3600)
            )

            # 生成公网 URL（如果 bucket 公开）
            public_url = f"https://{settings.OSS_BUCKET_NAME}.{settings.OSS_ENDPOINT}/{oss_key}"

            logger.info(
                f"临时文件上传成功:\n"
                f"  OSS Key: {oss_key}\n"
                f"  过期时间: {expiry_time.isoformat()}\n"
                f"  签名URL有效期: {expiry_hours}小时"
            )

            return {
                'oss_key': oss_key,
                'signed_url': signed_url,
                'public_url': public_url,
                'expiry_time': expiry_time.isoformat()
            }

        except Exception as e:
            logger.error(f"上传临时文件失败: {str(e)}", exc_info=True)
            raise RuntimeError(f"OSS 上传失败: {str(e)}")

    def generate_signed_url(
        self,
        oss_key: str,
        expiry_seconds: Optional[int] = None,
        method: str = 'GET'
    ) -> str:
        """
        生成签名 URL

        Args:
            oss_key: OSS 对象 key
            expiry_seconds: 过期时间（秒），None 使用默认配置
            method: HTTP 方法（GET/PUT/POST 等）

        Returns:
            str: 签名 URL
        """
        self._check_bucket()

        expiry_seconds = expiry_seconds or settings.OSS_TEMP_URL_EXPIRY

        try:
            signed_url = self.bucket.sign_url(
                method,
                oss_key,
                expiry_seconds
            )

            logger.debug(f"生成签名URL: {oss_key}, 有效期: {expiry_seconds}秒")
            return signed_url

        except Exception as e:
            logger.error(f"生成签名URL失败: {str(e)}")
            raise

    async def delete_temp_file(self, oss_key: str) -> bool:
        """
        删除临时文件

        Args:
            oss_key: OSS 对象 key

        Returns:
            bool: 是否删除成功
        """
        self._check_bucket()

        try:
            self.bucket.delete_object(oss_key)
            logger.info(f"临时文件删除成功: {oss_key}")
            return True

        except Exception as e:
            logger.error(f"删除临时文件失败 {oss_key}: {str(e)}")
            return False

    async def cleanup_expired_files(self) -> Dict[str, int]:
        """
        清理过期的临时文件

        Returns:
            Dict: {
                'scanned': 扫描的文件数,
                'deleted': 删除的文件数,
                'failed': 删除失败的文件数
            }
        """
        self._check_bucket()

        stats = {
            'scanned': 0,
            'deleted': 0,
            'failed': 0
        }

        try:
            logger.info("开始清理过期临时文件...")
            current_time = datetime.now()

            # 列出所有临时文件
            for obj in oss2.ObjectIterator(self.bucket, prefix=self.temp_prefix):
                stats['scanned'] += 1

                try:
                    # 获取对象元数据
                    meta = self.bucket.get_object_meta(obj.key)
                    expiry_time_str = meta.headers.get('x-oss-meta-expiry-time')

                    if expiry_time_str:
                        expiry_time = datetime.fromisoformat(expiry_time_str)

                        # 检查是否过期
                        if current_time > expiry_time:
                            # 删除过期文件
                            if await self.delete_temp_file(obj.key):
                                stats['deleted'] += 1
                            else:
                                stats['failed'] += 1

                except Exception as e:
                    logger.warning(f"处理文件 {obj.key} 时出错: {str(e)}")
                    stats['failed'] += 1

            logger.info(
                f"临时文件清理完成:\n"
                f"  扫描: {stats['scanned']} 个\n"
                f"  删除: {stats['deleted']} 个\n"
                f"  失败: {stats['failed']} 个"
            )

            return stats

        except Exception as e:
            logger.error(f"清理过期文件失败: {str(e)}", exc_info=True)
            return stats

    async def batch_delete_temp_files(self, oss_keys: List[str]) -> Dict[str, int]:
        """
        批量删除临时文件

        Args:
            oss_keys: OSS 对象 key 列表

        Returns:
            Dict: {
                'total': 总数,
                'deleted': 成功删除数,
                'failed': 删除失败数
            }
        """
        self._check_bucket()

        stats = {
            'total': len(oss_keys),
            'deleted': 0,
            'failed': 0
        }

        try:
            # 使用 OSS batch delete API
            result = self.bucket.batch_delete_objects(oss_keys)

            stats['deleted'] = len(result.deleted_keys)
            stats['failed'] = stats['total'] - stats['deleted']

            logger.info(
                f"批量删除临时文件: 成功 {stats['deleted']}/{stats['total']}"
            )

            return stats

        except Exception as e:
            logger.error(f"批量删除文件失败: {str(e)}", exc_info=True)
            stats['failed'] = stats['total']
            return stats

    def is_oss_configured(self) -> bool:
        """检查 OSS 是否已配置"""
        return self.bucket is not None


# 单例实例
temp_storage_service = TempStorageService()
