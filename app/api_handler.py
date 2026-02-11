import uuid

import uvicorn
from aws_lambda_powertools import Logger
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import UJSONResponse
from mangum import Mangum
from starlette.middleware.exceptions import ExceptionMiddleware

from app import settings
from app.api.v1.api import router as api_v1_router
from app.middlewares import CorrelationIdMiddleware
from app.models.response.error import ErrorResponse, ValidationErrorResponse

logger = Logger()

app = FastAPI(debug=settings.debug, title="AuthApp", version="1.0.0")
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(GZipMiddleware)
app.add_middleware(ExceptionMiddleware, handlers=app.exception_handlers)
app.include_router(api_v1_router)

handler = Mangum(app)
handler = logger.inject_lambda_context(handler, clear_state=True, log_event=True)


@app.exception_handler(BotoCoreError)
@app.exception_handler(ClientError)
def botocore_error_handler(request: Request, error: BotoCoreError) -> UJSONResponse:
    error_id = uuid.uuid4()
    error_message = str(error) if settings.debug else "Internal Server Error"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    logger.exception(f"Received botocore error {error_id=}")

    return UJSONResponse(
        content=ErrorResponse(status=status_code, error=error_message).model_dump(
            by_alias=True
        ),
        status_code=status_code,
    )


@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, error: HTTPException) -> UJSONResponse:
    error_id = uuid.uuid4()
    logger.exception(f"Received http exception {error_id=}")

    return UJSONResponse(
        content=ErrorResponse(status=error.status_code, error=error.detail).model_dump(
            by_alias=True
        ),
        status_code=error.status_code,
    )


@app.exception_handler(RequestValidationError)
def request_validation_error_handler(
    request: Request, error: RequestValidationError
) -> UJSONResponse:
    error_id = uuid.uuid4()
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    logger.exception(f"Received request validation error {error_id=}")

    return UJSONResponse(
        content=ValidationErrorResponse(
            status=status_code,
            error="Validation Error",
            errors=jsonable_encoder(error.errors()),
        ).model_dump(by_alias=True),
        status_code=status_code,
    )


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run("app.api_handler:app", host="localhost", port=8080, reload=True)
