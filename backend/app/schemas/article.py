from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


ArticleTitle = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
]
ArticleSummary = (
    Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None
)
ArticleContent = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
ArticleStatus = Literal["draft", "published"]
PositiveId = Annotated[int, Field(gt=0, le=2**63 - 1)]


class CreateArticleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: ArticleTitle
    summary: ArticleSummary = None
    content: ArticleContent
    status: ArticleStatus = "draft"
    cover_file_id: PositiveId | None = None


class UpdateArticleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: ArticleTitle | None = None
    summary: ArticleSummary = None
    content: ArticleContent | None = None
    status: ArticleStatus | None = None
    cover_file_id: PositiveId | None = None

    @model_validator(mode="after")
    def reject_explicit_null_fields(self) -> "UpdateArticleRequest":
        for field_name in ("title", "content", "status"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError("Trường này không được nhận null.")
        return self


class ArticleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    summary: str | None
    content: str
    status: ArticleStatus
    author_id: int
    cover_file_id: int | None
    cover_url: str | None = None
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None

    @field_validator("created_at", "updated_at", "published_at")
    @classmethod
    def ensure_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class ArticleSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    summary: str | None
    status: ArticleStatus
    author_id: int
    cover_file_id: int | None
    cover_url: str | None = None
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None

    @field_validator("created_at", "updated_at", "published_at")
    @classmethod
    def ensure_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
