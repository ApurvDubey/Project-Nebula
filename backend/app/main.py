"""FastAPI application factory for Nebula.

Nebula is an open-source NotebookLM alternative that uses PageIndex tree
navigation instead of vector databases for RAG.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.llm_provider import patch_pageindex_defaults


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: initialize database and patch PageIndex defaults on startup."""
    await init_db()
    patch_pageindex_defaults()
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        FastAPI: The configured application instance.
    """
    app = FastAPI(
        title="Nebula",
        description="Open-source NotebookLM alternative using PageIndex tree navigation",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS — allow all origins during development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Register routers ─────────────────────────────────────────────
    from app.api.notebooks import router as notebooks_router
    from app.api.documents import router as documents_router
    from app.api.chat import router as chat_router
    from app.api.podcast import router as podcast_router

    app.include_router(notebooks_router)
    app.include_router(documents_router)
    app.include_router(chat_router)
    app.include_router(podcast_router)

    # ── Health check ─────────────────────────────────────────────────
    @app.get("/api/health", tags=["health"])
    async def health_check() -> dict[str, str]:
        """Return a simple health-check response."""
        return {"status": "ok"}

    return app


app = create_app()
