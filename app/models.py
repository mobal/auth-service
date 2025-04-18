from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class JWTToken(BaseModel):
    exp: int
    iat: int
    iss: str | None = None
    jti: str
    sub: Any
    user: dict[str, Any]


class User(CamelModel):
    id: str
    display_name: str
    email: EmailStr
    password: str
    username: str
    created_at: str
    deleted_at: str | None = None
    updated_at: str | None = None


class Token(CamelModel):
    token: str
