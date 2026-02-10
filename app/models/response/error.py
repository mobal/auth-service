import uuid
from collections.abc import Sequence

from app.models.models import CamelModel


class ErrorResponse(CamelModel):
    status: int
    id: uuid.UUID
    message: str


class ValidationErrorResponse(ErrorResponse):
    errors: Sequence[dict]
