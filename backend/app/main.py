from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.auth import router as auth_router
from app.api.v1.articles import router as articles_router
from app.api.v1.articles import manage_router
from app.core.config import API_PREFIX, PROJECT_ROOT, get_settings
from app.core.errors import register_error_handlers
from app.core.responses import ErrorResponse
from app.db.base import Base
from app.db.session import engine
import app.models.article  # noqa: F401


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Models must be imported before create_all().
    Base.metadata.create_all(engine)
    try:
        yield
    finally:
        engine.dispose()


settings = get_settings()
app = FastAPI(
    title="Báo Đây API",
    version="0.1.0",
    lifespan=lifespan,
    responses={422: {"model": ErrorResponse}},
)
register_error_handlers(app)
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(articles_router, prefix=API_PREFIX)
app.include_router(manage_router, prefix=API_PREFIX)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

frontend_directory = PROJECT_ROOT / "frontend"
if frontend_directory.is_dir():

    @app.get("/", include_in_schema=False)
    def frontend_home() -> RedirectResponse:
        return RedirectResponse("/frontend/")

    app.mount("/frontend", StaticFiles(directory=frontend_directory, html=True), name="frontend")
