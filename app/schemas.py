from pydantic.networks import EmailStr
from pydantic.types import constr

from app.models import CamelModel


class LoginSchema(CamelModel):
    email: EmailStr
    password: constr(min_length=3)


class RefreshSchema(CamelModel):
    refresh_token: constr()
