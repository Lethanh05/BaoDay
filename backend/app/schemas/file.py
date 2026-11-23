from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, field_validator


class FileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_name: str
    url: str
    mime_type: str
    size_bytes: int
    owner_id: int
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def ensure_utc(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
