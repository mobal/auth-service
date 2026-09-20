from pydantic import BaseModel


class GoogleOIDCState(BaseModel):
    state: str
    nonce: str
    pending_request_id: str
    created_at: str
    ttl: int
