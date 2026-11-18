from fastapi import APIRouter, status

from app.core.dependencies import CurrentUser
from app.core.responses import ApiResponse, ErrorResponse
from app.db.session import DbSession
from app.schemas.auth import LoginData, LoginRequest, RegisterRequest, UserRead
from app.services import auth

router = APIRouter(prefix="/auth", tags=["Tài khoản"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorResponse}},
)
def register(body: RegisterRequest, db: DbSession) -> ApiResponse[UserRead]:
    user = auth.create_user(db, body)
    return ApiResponse(data=UserRead.model_validate(user))


@router.post("/login", responses={401: {"model": ErrorResponse}})
def login(body: LoginRequest, db: DbSession) -> ApiResponse[LoginData]:
    return ApiResponse(data=auth.login(db, body))


@router.get("/me", responses={401: {"model": ErrorResponse}})
def me(user: CurrentUser) -> ApiResponse[UserRead]:
    return ApiResponse(data=UserRead.model_validate(user))
