from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

Username = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=50)]
NewPassword = Annotated[str, Field(min_length=8, max_length=128)]
LoginPassword = Annotated[str, Field(min_length=1, max_length=128)]
Email = Annotated[EmailStr, Field(max_length=254)]


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: Username
    email: Email
    password: NewPassword


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: Email
    password: LoginPassword


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    role: Literal["reader", "editor", "admin"]
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def ensure_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class LoginData(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserRead
