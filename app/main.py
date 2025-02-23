import uuid
from typing import Dict, Sequence

import uvicorn
from aws_lambda_powertools import Logger
from botocore.exceptions import BotoCoreError
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from mangum import Mangum
from starlette.middleware.exceptions import ExceptionMiddleware
from starlette.middleware.gzip import GZipMiddleware

from app import settings
from app.jwt_bearer import JWTBearer
from app.middlewares import CorrelationIdMiddleware
from app.models import CamelModel
from app.schemas import LoginSchema, RefreshSchema
from app.services import AuthService

auth_service = AuthService()
jwt_bearer = JWTBearer()
logger = Logger(utc=True)

app = FastAPI(debug=settings.debug, title="AuthApp", version="1.0.0")
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(GZipMiddleware)
app.add_middleware(ExceptionMiddleware, handlers=app.exception_handlers)

handler = Mangum(app)
handler = logger.inject_lambda_context(handler, clear_state=True, log_event=True)


class ErrorResponse(CamelModel):
    status: int
    id: uuid.UUID
    message: str


class ValidationErrorResponse(ErrorResponse):
    errors: Sequence[Dict]


@app.post("/api/v1/login", status_code=status.HTTP_200_OK)
async def login(body: LoginSchema) -> dict[str, str]:
    jwt_token, refresh_token = await auth_service.login(str(body.email), body.password)
    return {
        "token": jwt_token,
        "refreshToken": refresh_token,
    }


@app.get(
    "/api/v1/logout",
    dependencies=[Depends(jwt_bearer)],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout():
    await auth_service.logout(jwt_bearer.decoded_token)


@app.post(
    "/api/v1/refresh",
    dependencies=[Depends(jwt_bearer)],
    status_code=status.HTTP_200_OK,
)
async def refresh(body: RefreshSchema) -> dict[str, str]:
    jwt_token, refresh_token = await auth_service.refresh(body.refresh_token)
    return {"token": jwt_token, "refreshToken": refresh_token}


@app.exception_handler(BotoCoreError)
async def botocore_error_handler(
    request: Request, error: BotoCoreError
) -> JSONResponse:
    error_id = uuid.uuid4()
    error_message = str(error) if settings.debug else "Internal Server Error"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    logger.exception(f"Received botocore error {error_id=}")
    return JSONResponse(
        content=jsonable_encoder(
            ErrorResponse(status=status_code, id=error_id, message=error_message)
        ),
        status_code=status_code,
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request, error: HTTPException
) -> JSONResponse:
    error_id = uuid.uuid4()
    logger.exception(f"Received http exception {error_id=}")
    return JSONResponse(
        content=jsonable_encoder(
            ErrorResponse(status=error.status_code, id=error_id, message=error.detail)
        ),
        status_code=error.status_code,
    )


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    request: Request, error: RequestValidationError
) -> JSONResponse:
    error_id = uuid.uuid4()
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    logger.exception(f"Received request validation error {error_id=}")
    return JSONResponse(
        content=jsonable_encoder(
            ValidationErrorResponse(
                status=status_code,
                id=error_id,
                message=str(error),
                errors=error.errors(),
            )
        ),
        status_code=status_code,
    )


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="localhost", port=3000, reload=True)
