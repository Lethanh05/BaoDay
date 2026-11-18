from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.auth import router as auth_router
from app.core.config import API_PREFIX, get_settings
from app.core.errors import register_error_handlers
from app.core.responses import ErrorResponse
from app.db.base import Base
from app.db.session import engine


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Auth router imports User. Import the article and file models before this
    # call when their modules are integrated.
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

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
