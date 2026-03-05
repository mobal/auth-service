from fastapi import Form
from pydantic import BaseModel


class OAuthRevokeRequest(BaseModel):
    token: str

    @classmethod
    def as_form(cls, token: str = Form(...)) -> "OAuthRevokeRequest":
        return cls(token=token)
