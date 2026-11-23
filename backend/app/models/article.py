from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.file import file_url


class ArticleStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str | None] = mapped_column(String(500), default=None)
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[ArticleStatus] = mapped_column(
        Enum(
            ArticleStatus,
            name="article_status",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        default=ArticleStatus.DRAFT,
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        index=True,
    )
    cover_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("files.id", ondelete="RESTRICT"),
        index=True,
        default=None,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
    )

    @property
    def cover_url(self) -> str | None:
        return file_url(self.cover_file_id) if self.cover_file_id is not None else None
