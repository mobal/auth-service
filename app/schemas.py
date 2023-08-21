from pydantic.networks import EmailStr
from pydantic.types import constr

from app.services import CamelModel


class Login(CamelModel):
    email: EmailStr
    password: constr(min_length=3)
