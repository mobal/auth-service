from pydantic import BaseModel


class LoginPage(BaseModel):
    request_id: str
    csrf_token: str
    error: str | None = None
