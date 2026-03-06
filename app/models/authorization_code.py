from pydantic import BaseModel


class AuthorizationCode(BaseModel):
    code: str
    client_id: str
    user_id: str
    redirect_uri: str
    scope: str | None = None
    code_challenge: str | None = None
    code_challenge_method: str | None = None
    ttl: int
