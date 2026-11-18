from typing import Generic, TypeVar

from pydantic import BaseModel

Data = TypeVar("Data")


class ApiResponse(BaseModel, Generic[Data]):
    data: Data


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class PageResponse(ApiResponse[list[Data]], Generic[Data]):
    meta: PaginationMeta


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
