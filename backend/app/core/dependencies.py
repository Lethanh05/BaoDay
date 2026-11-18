from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError

from app.core.errors import ApiError
from app.core.security import decode_access_token
from app.db.session import DbSession
from app.models.user import Role, User

bearer_scheme = HTTPBearer(auto_error=False)


def unauthorized() -> ApiError:
    return ApiError(
        401,
        "UNAUTHORIZED",
        "Cần token hợp lệ để truy cập.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: DbSession,
) -> User:
    if credentials is None:
        raise unauthorized()
    try:
        user_id = decode_access_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise unauthorized() from exc

    user = db.get(User, user_id)
    if user is None:
        raise unauthorized()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: Role) -> Callable[..., User]:
    def check_role(user: CurrentUser) -> User:
        if user.role not in roles:
            raise ApiError(403, "FORBIDDEN", "Bạn không có quyền thực hiện thao tác này.")
        return user

    return check_role
