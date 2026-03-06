from fastapi import Form
from pydantic import BaseModel


class OAuthTokenRequest(BaseModel):
    grant_type: str
    username: str | None = None
    password: str | None = None
    refresh_token: str | None = None
    code: str | None = None
    code_verifier: str | None = None
    redirect_uri: str | None = None
    scope: str | None = None

    @classmethod
    def as_form(
        cls,
        grant_type: str = Form(...),
        username: str | None = Form(None),
        password: str | None = Form(None),
        refresh_token: str | None = Form(None),
        code: str | None = Form(None),
        code_verifier: str | None = Form(None),
        redirect_uri: str | None = Form(None),
        scope: str | None = Form(None),
    ) -> "OAuthTokenRequest":
        return cls(
            grant_type=grant_type,
            username=username,
            password=password,
            refresh_token=refresh_token,
            code=code,
            code_verifier=code_verifier,
            redirect_uri=redirect_uri,
            scope=scope,
        )
