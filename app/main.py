"""
FastAPI应用主入口
集成完善的中间件系统和异常处理
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.utils.logger import setup_logging, get_logger
from app.core.middleware import (
    RequestIDMiddleware,
    RequestTimingMiddleware,
    ExceptionHandlerMiddleware,
    CORSSecurityMiddleware,
)
from app.api.v1 import videos, tasks

# 设置日志
setup_logging(log_level="DEBUG" if settings.DEBUG else "INFO")
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("application_starting", version=settings.APP_VERSION)

    # 创建必要的目录
    import os
    for directory in [
        settings.uploads_dir,
        settings.processed_dir,
        settings.cache_dir,
        settings.metadata_dir,
    ]:
        os.makedirs(directory, exist_ok=True)

    logger.info("storage_directories_created")

    yield

    # 关闭时
    logger.info("application_shutting_down")


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI驱动的自动视频剪辑系统",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    lifespan=lifespan,
)

# ===== 中间件配置 =====
# 注意：中间件按照添加顺序执行，后添加的先执行

# 1. 安全中间件（最先执行）
app.add_middleware(CORSSecurityMiddleware)

# 2. CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应配置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time"],
)

# 3. 请求计时中间件
app.add_middleware(RequestTimingMiddleware)

# 4. 请求ID中间件
app.add_middleware(RequestIDMiddleware)

# 5. 全局异常处理中间件（最后执行，捕获所有异常）
app.add_middleware(ExceptionHandlerMiddleware)


# 健康检查
@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


# 根路径
@app.get("/")
async def root():
    """根路径"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": f"{settings.API_V1_PREFIX}/docs",
    }


# 注册路由
app.include_router(
    videos.router,
    prefix=f"{settings.API_V1_PREFIX}/videos",
    tags=["Videos"],
)

app.include_router(
    tasks.router,
    prefix=f"{settings.API_V1_PREFIX}/tasks",
    tags=["Tasks"],
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
    )
