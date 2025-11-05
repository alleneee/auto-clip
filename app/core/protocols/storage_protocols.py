"""
存储服务抽象接口 (SOLID: 依赖倒置原则)
"""
from typing import Protocol, Dict, Optional


class IStorageService(Protocol):
    """对象存储服务接口 (支持OSS/S3/本地等)"""

    async def upload(
        self,
        local_path: str,
        remote_path: str,
        content_type: Optional[str] = None
    ) -> Dict[str, str]:
        """
        上传文件到存储服务

        Args:
            local_path: 本地文件路径
            remote_path: 远程路径
            content_type: 内容类型

        Returns:
            包含public_url等信息的字典
        """
        ...
