from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import SecretStr, field_validator, model_validator
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

PROJECT_ROOT = Path(__file__).resolve().parents[3]
API_PREFIX = "/api/v1"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8-sig",
        hide_input_in_errors=True,
    )

    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite:///backend/baoday.db"
    jwt_secret_key: SecretStr
    access_token_expire_minutes: int = Field(default=30, gt=0)
    upload_dir: Path = Path("backend/uploads")
    max_upload_size_mb: int = Field(default=5, gt=0)
    allowed_upload_types: list[str] = Field(
        default_factory=lambda: ["image/jpeg", "image/png", "image/webp"]
    )
    cors_origins: list[str] = Field(default_factory=list)

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value().encode("utf-8")) < 32:
            raise ValueError("JWT_SECRET_KEY phải có ít nhất 32 byte.")
        return value

    @model_validator(mode="after")
    def resolve_local_paths(self) -> Self:
        if not self.upload_dir.is_absolute():
            self.upload_dir = PROJECT_ROOT / self.upload_dir

        url = make_url(self.database_url)
        if url.get_backend_name() == "sqlite" and url.database not in (None, ":memory:"):
            if not url.query.get("uri") and not Path(url.database).is_absolute():
                url = url.set(database=(PROJECT_ROOT / url.database).as_posix())
                self.database_url = url.render_as_string(hide_password=False)
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
