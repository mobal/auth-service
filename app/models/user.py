from pydantic import EmailStr

from app.models.models import CamelModel


class User(CamelModel):
    id: str
    display_name: str | None = None
    email: EmailStr
    password: str
    username: str
    created_at: str
    deleted_at: str | None = None
    updated_at: str | None = None
