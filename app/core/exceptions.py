"""
自定义异常类
"""


class AutoClipException(Exception):
    """基础异常类"""

    def __init__(self, message: str, recoverable: bool = False):
        self.message = message
        self.recoverable = recoverable
        super().__init__(self.message)


class VideoProcessingError(AutoClipException):
    """视频处理异常"""
    pass


class VideoNotFoundError(AutoClipException):
    """视频未找到"""
    pass


class VideoFormatError(AutoClipException):
    """视频格式错误"""
    pass


class VideoTooLargeError(AutoClipException):
    """视频文件过大"""
    pass


class AnalysisError(AutoClipException):
    """视频分析异常"""
    pass


class LLMServiceError(AutoClipException):
    """LLM服务异常"""
    pass


class ClipExecutionError(AutoClipException):
    """剪辑执行异常"""
    pass


class StorageError(AutoClipException):
    """存储异常"""
    pass


class OSSUploadError(StorageError):
    """OSS上传异常"""
    pass


class WebhookError(AutoClipException):
    """Webhook通知异常"""
    pass


class TaskNotFoundError(AutoClipException):
    """任务未找到"""
    pass


class ConfigurationError(AutoClipException):
    """配置错误"""
    pass
