from pydantic import BaseModel


class PendingAuthorizationRequest(BaseModel):
    id: str
    client_id: str
    redirect_uri: str
    response_type: str
    scope: str | None = None
    state: str | None = None
    code_challenge: str
    code_challenge_method: str
    csrf_token: str
    created_at: str
    ttl: int
