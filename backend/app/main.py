"""FastAPI 应用入口。"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .core.storage import get_storage
from .core.task_manager import task_manager
from .api.routes import projects, tasks, voices, avatars, media, publishers
from .providers import registry  # noqa: F401  触发 Provider 注册

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task_manager.start()
    logger.info("AutoTalk Studio backend started")
    yield
    task_manager.stop()
    logger.info("AutoTalk Studio backend stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AutoTalk Studio",
        description="AI 数字人口播视频自动生产系统",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 静态文件：让前端可直接访问生成的视频/音频
    app.mount("/static", StaticFiles(directory=str(get_storage().root)), name="static")

    # 路由
    api_prefix = "/api"
    app.include_router(projects.router, prefix=api_prefix)
    app.include_router(tasks.router, prefix=api_prefix)
    app.include_router(voices.router, prefix=api_prefix)
    app.include_router(avatars.router, prefix=api_prefix)
    app.include_router(media.router, prefix=api_prefix)
    app.include_router(publishers.router, prefix=api_prefix)

    @app.get("/")
    async def root():
        return {
            "name": "AutoTalk Studio",
            "version": "0.1.0",
            "docs": "/docs",
            "providers": registry.list_providers(),
        }

    @app.get("/api/providers")
    async def list_providers(type_: str | None = None):
        return registry.list_providers(type_filter=type_)

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    s = get_settings()
    uvicorn.run(app, host=s.host, port=s.port)
