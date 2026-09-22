from typing import Literal

from pydantic import BaseModel

from app.models.pending_authorization_request import PendingAuthorizationRequest


class GoogleLoginResult(BaseModel):
    status: Literal["invalid_request", "error", "success"]
    pending: PendingAuthorizationRequest | None = None
    user_id: str | None = None
    error_message: str | None = None
