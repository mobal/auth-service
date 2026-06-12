import time
from collections.abc import Sequence

from app.models.models import CamelModel


class ErrorResponse(CamelModel):
    """OAuth 2.0 error response (RFC 6749 Section 5.2).

    Returned with a 4xx status code when a request fails.
    The ``error`` field contains a machine-readable OAuth error code;
    human-readable descriptions are included in ``error_description``.
    """

    status: int
    """HTTP status code of the error response."""
    error: str
    """OAuth 2.0 error code (e.g. ``\"invalid_request\"``, ``\"invalid_grant\"``)."""
    timestamp: int = int(time.time())
    """Unix timestamp when the error occurred."""


class ValidationErrorResponse(ErrorResponse):
    """Error response with per-field validation details.

    Used when request body validation fails (e.g. missing required fields,
    type mismatches).  The ``errors`` list contains field-level messages.
    """

    errors: Sequence[dict]
    """Sequence of dicts, each describing a specific validation failure."""
