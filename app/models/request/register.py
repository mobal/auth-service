from app.models.models import CamelModel


class RegistrationRequest(CamelModel):
    email: str
    username: str
    password: str
    display_name: str
