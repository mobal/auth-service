from app.models.models import CamelModel


class RefreshRequest(CamelModel):
    refresh_token: str
