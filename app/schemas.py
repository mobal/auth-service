from fastapi_camelcase import CamelModel


class Login(CamelModel):
    email: str
    password: str
