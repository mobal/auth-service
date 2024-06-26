import uuid
from contextvars import ContextVar

from aws_lambda_powertools import Logger
from starlette.middleware.base import (BaseHTTPMiddleware,
                                       RequestResponseEndpoint)
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

X_CORRELATION_ID = "X-Correlation-ID"
correlation_id: ContextVar[str | None] = ContextVar(
    X_CORRELATION_ID, default=str(uuid.uuid4())
)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self._logger = Logger(utc=True)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.headers.get(X_CORRELATION_ID):
            correlation_id.set(request.headers[X_CORRELATION_ID])
        self._logger.set_correlation_id(correlation_id.get())
        response = await call_next(request)
        response.headers[X_CORRELATION_ID] = correlation_id.get()
        return response
