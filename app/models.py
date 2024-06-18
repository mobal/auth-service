from typing import Any, Optional

from humps import camelize
from pydantic import BaseModel, ConfigDict, EmailStr


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=camelize, populate_by_name=True)


class Cache(CamelModel):
    key: str
    value: Any
    created_at: str
    ttl: int


class JWTToken(BaseModel):
    exp: int
    iat: int
    iss: Optional[str] = None
    jti: str
    sub: Any


class User(CamelModel):
    id: str
    display_name: str
    email: EmailStr
    password: str
    roles: list[str]
    username: str
    created_at: str
    deleted_at: Optional[str] = None
    updated_at: Optional[str] = None


class Token(CamelModel):
    token: str
