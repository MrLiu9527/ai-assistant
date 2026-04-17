"""FastAPI 应用配置"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from src.agents import agent_manager
from src.api.v1 import router as api_v1_router
from src.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("Starting AI-Assistant API server...")

    # 初始化 Agent 管理器
    try:
        await agent_manager.initialize()
        logger.info("Agent manager initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize agent manager: {e}")

    yield

    # 关闭时
    logger.info("Shutting down AI-Assistant API server...")


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title="AI-Assistant API",
        description="AI-Assistant 数字员工平台 API",
        version="1.0.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
        lifespan=lifespan,
    )

    # 配置 CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册异常处理器
    register_exception_handlers(app)

    # 注册路由
    app.include_router(api_v1_router, prefix="/api/v1")

    # 健康检查
    @app.get("/health", tags=["health"])
    async def health_check():
        return {"status": "ok", "service": "ai-assistant"}

    @app.get("/", tags=["root"])
    async def root():
        return {
            "name": "AI-Assistant API",
            "version": "1.0.0",
            "docs": "/docs" if settings.debug else None,
        }

    return app


def register_exception_handlers(app: FastAPI) -> None:
    """注册异常处理器"""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """请求验证错误"""
        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(x) for x in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            })

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "code": 422,
                "message": "Validation error",
                "detail": errors,
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """全局异常处理"""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": 500,
                "message": "Internal server error",
                "detail": str(exc) if settings.debug else None,
            },
        )


# 创建应用实例
app = create_app()
