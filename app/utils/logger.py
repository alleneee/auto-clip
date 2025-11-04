"""
日志配置模块
"""
import logging
import sys
from pathlib import Path
import structlog
from structlog.typing import EventDict


def add_app_context(logger, method_name, event_dict: EventDict) -> EventDict:
    """添加应用上下文信息"""
    event_dict["app"] = "auto-clip"
    return event_dict


def setup_logging(log_level: str = "INFO"):
    """
    配置结构化日志

    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # 确保日志目录存在
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # 配置structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            add_app_context,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # 配置标准logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    # 文件处理器
    file_handler = logging.FileHandler(log_dir / "auto-clip.log")
    file_handler.setLevel(getattr(logging, log_level.upper()))
    logging.getLogger().addHandler(file_handler)


def get_logger(name: str = None):
    """
    获取日志器

    Args:
        name: 日志器名称

    Returns:
        structlog日志器实例
    """
    return structlog.get_logger(name)


# 便捷访问
logger = get_logger(__name__)
