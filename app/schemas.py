from fastapi_camelcase import CamelModel
from pydantic.networks import EmailStr


class CreateUser(CamelModel):
    display_name: str
    email: EmailStr
    confirm_password: str
    password: str


class Login(CamelModel):
    email: str
    password: str


class Register(CamelModel):
    email: str
    password: str
