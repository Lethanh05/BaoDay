from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query, status

from app.core.dependencies import require_roles
from app.core.responses import ApiResponse, PageResponse, PaginationMeta
from app.db.session import DbSession
from app.models.user import Role, User
from app.schemas.article import (
    ArticleRead,
    ArticleSummaryRead,
    CreateArticleRequest,
    UpdateArticleRequest,
)
from app.services import articles

router = APIRouter(prefix="/articles", tags=["Bài viết"])
manage_router = APIRouter(prefix="/manage/articles", tags=["Quản lý bài viết"])

Page = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]
ArticleId = Annotated[int, Path(gt=0, le=2**63 - 1)]
ManageUser = Annotated[
    User,
    Depends(require_roles(Role.EDITOR, Role.ADMIN)),
]


@router.get("")
def public_article_list(
    db: DbSession,
    page: Page = 1,
    page_size: PageSize = 10,
) -> PageResponse[ArticleSummaryRead]:
    records, total, total_pages = articles.list_published_articles(
        db,
        page,
        page_size,
    )
    return PageResponse(
        data=[ArticleSummaryRead.model_validate(record) for record in records],
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        ),
    )


@router.get("/{article_id}")
def public_article_detail(
    article_id: ArticleId,
    db: DbSession,
) -> ApiResponse[ArticleRead]:
    record = articles.get_published_article(db, article_id)
    return ApiResponse(data=ArticleRead.model_validate(record))


@router.post("", status_code=status.HTTP_201_CREATED)
def create_article(
    body: CreateArticleRequest,
    db: DbSession,
    user: ManageUser,
) -> ApiResponse[ArticleRead]:
    record = articles.create_article(db, body, user)
    return ApiResponse(data=ArticleRead.model_validate(record))


@router.patch("/{article_id}")
def update_article(
    article_id: ArticleId,
    body: UpdateArticleRequest,
    db: DbSession,
    user: ManageUser,
) -> ApiResponse[ArticleRead]:
    record = articles.update_article(db, article_id, body, user)
    return ApiResponse(data=ArticleRead.model_validate(record))


@router.delete("/{article_id}")
def delete_article(
    article_id: ArticleId,
    db: DbSession,
    user: ManageUser,
) -> ApiResponse[dict[str, int]]:
    deleted_id = articles.delete_article(db, article_id, user)
    return ApiResponse(data={"id": deleted_id})


@manage_router.get("")
def managed_article_list(
    db: DbSession,
    user: ManageUser,
    q: Annotated[str | None, Query(max_length=200)] = None,
    status: Literal["draft", "published"] | None = None,
    sort_by: Literal["title", "created_at", "updated_at"] = "created_at",
    order: Literal["asc", "desc"] = "desc",
    page: Page = 1,
    page_size: PageSize = 10,
) -> PageResponse[ArticleRead]:
    records, total, total_pages = articles.list_managed_articles(
        db=db,
        user=user,
        q=q,
        status=status,
        sort_by=sort_by,
        order=order,
        page=page,
        page_size=page_size,
    )
    return PageResponse(
        data=[ArticleRead.model_validate(record) for record in records],
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        ),
    )
