from app.models.models import CamelModel


class ServiceCredential(CamelModel):
    id: str
    name: str
    secret: str
    scopes: list[str] = []
    created_at: str
