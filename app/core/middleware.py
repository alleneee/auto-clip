"""
中间件系统
包含异常处理、请求追踪、日志记录等中间件
"""
import time
import uuid
import traceback
from typing import Callable
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.core.exceptions import AutoClipException
from app.models.responses import ErrorResponse, ErrorDetail, ValidationErrorResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    请求ID中间件
    为每个请求生成唯一ID，用于日志追踪和调试
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求，添加请求ID"""
        # 生成或使用已有的请求ID
        request_id = request.headers.get("X-Request-ID", f"req_{uuid.uuid4().hex[:12]}")

        # 将请求ID添加到请求状态中
        request.state.request_id = request_id

        # 记录请求开始
        logger.info(
            "request_started",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
        )

        # 处理请求
        response = await call_next(request)

        # 将请求ID添加到响应头
        response.headers["X-Request-ID"] = request_id

        return response


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """
    请求计时中间件
    记录每个请求的处理时间
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求，记录处理时间"""
        start_time = time.time()

        # 处理请求
        response = await call_next(request)

        # 计算处理时间
        process_time = time.time() - start_time

        # 添加处理时间到响应头
        response.headers["X-Process-Time"] = f"{process_time:.4f}"

        # 记录请求完成
        request_id = getattr(request.state, "request_id", "unknown")
        logger.info(
            "request_completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            process_time=f"{process_time:.4f}s",
        )

        return response


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """
    全局异常处理中间件
    捕获并处理所有未处理的异常，返回统一的错误响应
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求，捕获异常"""
        try:
            response = await call_next(request)
            return response

        except AutoClipException as exc:
            # 自定义业务异常
            return await self._handle_autoclip_exception(request, exc)

        except RequestValidationError as exc:
            # 请求验证异常（Pydantic）
            return await self._handle_validation_exception(request, exc)

        except StarletteHTTPException as exc:
            # HTTP异常
            return await self._handle_http_exception(request, exc)

        except Exception as exc:
            # 未预期的异常
            return await self._handle_unexpected_exception(request, exc)

    async def _handle_autoclip_exception(
        self, request: Request, exc: AutoClipException
    ) -> JSONResponse:
        """处理自定义业务异常"""
        request_id = getattr(request.state, "request_id", "unknown")

        # 记录异常
        logger.warning(
            "autoclip_exception",
            request_id=request_id,
            exception_type=exc.__class__.__name__,
            message=exc.message,
            recoverable=exc.recoverable,
            path=request.url.path,
        )

        # 构建错误响应
        error_response = ErrorResponse(
            error=ErrorDetail(
                code=exc.__class__.__name__.upper().replace("ERROR", ""),
                message=exc.message,
                detail=traceback.format_exc() if settings.DEBUG else None,
            ),
            path=str(request.url.path),
            method=request.method,
            request_id=request_id,
        )

        # 根据异常类型确定HTTP状态码
        status_code = self._get_status_code_for_exception(exc)

        return JSONResponse(
            status_code=status_code,
            content=error_response.model_dump(mode="json"),
        )

    async def _handle_validation_exception(
        self, request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """处理请求验证异常"""
        request_id = getattr(request.state, "request_id", "unknown")

        # 记录验证错误
        logger.warning(
            "validation_error",
            request_id=request_id,
            path=request.url.path,
            errors=exc.errors(),
        )

        # 构建验证错误响应
        errors = []
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            errors.append(
                ErrorDetail(
                    code="VALIDATION_ERROR",
                    message=error["msg"],
                    field=field,
                    detail=error.get("ctx") if settings.DEBUG else None,
                )
            )

        validation_response = ValidationErrorResponse(
            errors=errors,
            path=str(request.url.path),
            request_id=request_id,
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=validation_response.model_dump(mode="json"),
        )

    async def _handle_http_exception(
        self, request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """处理HTTP异常"""
        request_id = getattr(request.state, "request_id", "unknown")

        # 记录HTTP异常
        logger.warning(
            "http_exception",
            request_id=request_id,
            status_code=exc.status_code,
            detail=exc.detail,
            path=request.url.path,
        )

        # 构建错误响应
        error_response = ErrorResponse(
            error=ErrorDetail(
                code=f"HTTP_{exc.status_code}",
                message=exc.detail or "请求失败",
            ),
            path=str(request.url.path),
            method=request.method,
            request_id=request_id,
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.model_dump(mode="json"),
        )

    async def _handle_unexpected_exception(
        self, request: Request, exc: Exception
    ) -> JSONResponse:
        """处理未预期的异常"""
        request_id = getattr(request.state, "request_id", "unknown")

        # 记录严重错误
        logger.error(
            "unexpected_exception",
            request_id=request_id,
            exception_type=exc.__class__.__name__,
            exception_message=str(exc),
            traceback=traceback.format_exc(),
            path=request.url.path,
        )

        # 构建错误响应
        error_response = ErrorResponse(
            error=ErrorDetail(
                code="INTERNAL_SERVER_ERROR",
                message="服务器内部错误" if not settings.DEBUG else str(exc),
                detail=traceback.format_exc() if settings.DEBUG else None,
            ),
            path=str(request.url.path),
            method=request.method,
            request_id=request_id,
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response.model_dump(mode="json"),
        )

    def _get_status_code_for_exception(self, exc: AutoClipException) -> int:
        """根据异常类型返回对应的HTTP状态码"""
        from app.core.exceptions import (
            VideoNotFoundError,
            TaskNotFoundError,
            VideoFormatError,
            VideoTooLargeError,
            StorageError,
            ConfigurationError,
        )

        # 404 Not Found
        if isinstance(exc, (VideoNotFoundError, TaskNotFoundError)):
            return status.HTTP_404_NOT_FOUND

        # 400 Bad Request
        if isinstance(exc, (VideoFormatError, VideoTooLargeError, ConfigurationError)):
            return status.HTTP_400_BAD_REQUEST

        # 503 Service Unavailable
        if isinstance(exc, StorageError):
            return status.HTTP_503_SERVICE_UNAVAILABLE

        # 默认 500 Internal Server Error
        return status.HTTP_500_INTERNAL_SERVER_ERROR


class CORSSecurityMiddleware(BaseHTTPMiddleware):
    """
    CORS安全中间件
    添加安全相关的响应头
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求，添加安全头"""
        response = await call_next(request)

        # 添加安全头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # 生产环境添加严格传输安全
        if not settings.DEBUG:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        return response
