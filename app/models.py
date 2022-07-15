from fastapi_camelcase import CamelModel
from pydantic.networks import EmailStr


class Cache(CamelModel):
    key: str
    value: str
    expired_at: str


class User(CamelModel):
    id: str
    display_name: str
    email: EmailStr
    password: str
    roles: list[str]
    username: str
    created_at: str
    deleted_at: str
    updated_at: str


class Token(CamelModel):
    token: str
