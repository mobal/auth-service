from pydantic import EmailStr, constr

from app.models.models import CamelModel


class LoginSchema(CamelModel):
    email: EmailStr
    password: constr(min_length=3)
