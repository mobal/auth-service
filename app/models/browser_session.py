from pydantic import BaseModel


class BrowserSession(BaseModel):
    id: str
    user_id: str
    created_at: str
    ttl: int
