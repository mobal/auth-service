from pydantic import BaseModel

from app.models.pending_authorization_request import PendingAuthorizationRequest


class AuthorizationDecision(BaseModel):
    redirect_uri: str
    state: str | None = None
    authorization_code: str | None = None
    pending_request: PendingAuthorizationRequest | None = None
