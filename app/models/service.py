from app.models.models import CamelModel


class ServiceCredential(CamelModel):
    id: str
    secret: str
    scopes: list[str] = []
    created_at: str
