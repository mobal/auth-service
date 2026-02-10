from pydantic import constr

from app.models.models import CamelModel


class RefreshSchema(CamelModel):
    refresh_token: constr()
