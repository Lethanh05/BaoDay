from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.security import dummy_password_hash, hash_password, issue_access_token, verify_password
from app.models.user import Role, User
from app.schemas.auth import LoginData, LoginRequest, RegisterRequest, UserRead


def find_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.casefold()))


def create_user(db: Session, data: RegisterRequest, role: Role = Role.EDITOR) -> User:
    if find_user_by_email(db, data.email) is not None:
        raise ApiError(409, "EMAIL_EXISTS", "Email đã được đăng ký.")

    user = User(
        username=data.username,
        email=data.email.casefold(),
        password_hash=hash_password(data.password),
        role=role,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if find_user_by_email(db, data.email) is not None:
            raise ApiError(409, "EMAIL_EXISTS", "Email đã được đăng ký.") from exc
        raise
    return user


def login(db: Session, data: LoginRequest) -> LoginData:
    user = find_user_by_email(db, data.email)
    stored_hash = user.password_hash if user is not None else dummy_password_hash()
    if not verify_password(data.password, stored_hash) or user is None:
        raise ApiError(401, "INVALID_CREDENTIALS", "Email hoặc mật khẩu không đúng.")

    token, expires_in = issue_access_token(user.id)
    return LoginData(access_token=token, expires_in=expires_in, user=UserRead.model_validate(user))
