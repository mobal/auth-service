from fastapi_camelcase import CamelModel
from pydantic.networks import EmailStr
from pydantic.types import constr


class Login(CamelModel):
    email: EmailStr
    password: constr(min_length=3)
