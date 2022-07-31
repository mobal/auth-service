from typing import Any, Optional

from fastapi_camelcase import CamelModel
from pydantic import BaseModel
from pydantic.networks import EmailStr


class Cache(CamelModel):
    key: str
    value: Any
    created_at: str
    ttl: int


class JWTToken(BaseModel):
    exp: int
    iat: int
    iss: Optional[str]
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
    deleted_at: Optional[str]
    updated_at: Optional[str]


class Token(CamelModel):
    token: str
