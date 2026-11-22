from datetime import UTC, datetime
from math import ceil

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models.article import Article, ArticleStatus
from app.models.user import Role, User
from app.schemas.article import CreateArticleRequest, UpdateArticleRequest


def ensure_can_manage(article: Article, user: User) -> None:
    if user.role == Role.ADMIN:
        return
    if user.role == Role.EDITOR and article.author_id == user.id:
        return
    raise ApiError(403, "FORBIDDEN", "Bạn không có quyền quản lý bài viết này.")


def create_article(
    db: Session,
    data: CreateArticleRequest,
    user: User,
) -> Article:
    now = datetime.now(UTC)
    status = ArticleStatus(data.status)
    article = Article(
        title=data.title,
        summary=data.summary,
        content=data.content,
        status=status,
        author_id=user.id,
        cover_file_id=data.cover_file_id,
        created_at=now,
        updated_at=now,
        published_at=now if status == ArticleStatus.PUBLISHED else None,
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return article


def update_article(
    db: Session,
    article_id: int,
    data: UpdateArticleRequest,
    user: User,
) -> Article:
    article = db.get(Article, article_id)
    if article is None:
        raise ApiError(404, "NOT_FOUND", "Không tìm thấy bài viết.")
    ensure_can_manage(article, user)

    sent_fields = data.model_fields_set
    for field_name in ("title", "summary", "content", "cover_file_id"):
        if field_name in sent_fields:
            setattr(article, field_name, getattr(data, field_name))

    if "status" in sent_fields:
        new_status = ArticleStatus(data.status)
        if new_status == ArticleStatus.PUBLISHED:
            if article.status != ArticleStatus.PUBLISHED:
                article.published_at = datetime.now(UTC)
        else:
            article.published_at = None
        article.status = new_status

    article.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(article)
    return article


def delete_article(db: Session, article_id: int, user: User) -> int:
    article = db.get(Article, article_id)
    if article is None:
        raise ApiError(404, "NOT_FOUND", "Không tìm thấy bài viết.")
    ensure_can_manage(article, user)
    db.delete(article)
    db.commit()
    return article_id


def list_published_articles(
    db: Session,
    page: int,
    page_size: int,
) -> tuple[list[Article], int, int]:
    filters = Article.status == ArticleStatus.PUBLISHED
    total = db.scalar(select(func.count()).select_from(Article).where(filters)) or 0
    total_pages = ceil(total / page_size) if total else 0

    articles = list(
        db.scalars(
            select(Article)
            .where(filters)
            .order_by(
                Article.published_at.desc(),
                Article.created_at.desc(),
                Article.id.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return articles, total, total_pages


def get_published_article(db: Session, article_id: int) -> Article:
    article = db.scalar(
        select(Article).where(
            Article.id == article_id,
            Article.status == ArticleStatus.PUBLISHED,
        )
    )
    if article is None:
        raise ApiError(404, "NOT_FOUND", "Không tìm thấy bài viết.")
    return article


def list_managed_articles(
    db: Session,
    user: User,
    q: str | None,
    status: str | None,
    sort_by: str,
    order: str,
    page: int,
    page_size: int,
) -> tuple[list[Article], int, int]:
    filters = []
    if user.role == Role.EDITOR:
        filters.append(Article.author_id == user.id)

    if q and q.strip():
        keyword = f"%{q.strip()}%"
        filters.append(
            Article.title.ilike(keyword) | Article.summary.ilike(keyword)
        )

    if status:
        filters.append(Article.status == ArticleStatus(status))

    count_statement = select(func.count()).select_from(Article)
    if filters:
        count_statement = count_statement.where(*filters)
    total = db.scalar(count_statement) or 0
    total_pages = ceil(total / page_size) if total else 0

    sort_columns = {
        "title": Article.title,
        "created_at": Article.created_at,
        "updated_at": Article.updated_at,
    }
    sort_column = sort_columns[sort_by]
    sort_direction = sort_column.desc() if order == "desc" else sort_column.asc()

    statement = select(Article)
    if filters:
        statement = statement.where(*filters)
    statement = (
        statement
        .order_by(sort_direction, Article.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    records = list(db.scalars(statement))
    return records, total, total_pages
