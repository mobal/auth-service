import uuid
from inspect import isclass
from typing import Dict, List

import botocore
import uvicorn
from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.metrics import MetricUnit
from botocore.exceptions import BotoCoreError
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi_camelcase import CamelModel
from mangum import Mangum
from starlette import status
from starlette.middleware.exceptions import ExceptionMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.responses import JSONResponse

from app.auth import JWTBearer
from app.middlewares import CorrelationIdMiddleware
from app.schemas import Login
from app.services import AuthService, Token
from app.settings import Settings

auth_service = AuthService()
jwt_bearer = JWTBearer()
logger = Logger(utc=True)
metrics = Metrics()
settings = Settings()
tracer = Tracer()

app = FastAPI(debug=settings.app_debug, title='AuthApp', version='1.0.0')
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(GZipMiddleware)
app.add_middleware(ExceptionMiddleware, handlers=app.exception_handlers)

handler = Mangum(app)
handler.__name__ = 'handler'
handler = tracer.capture_lambda_handler(handler)
handler = logger.inject_lambda_context(handler, clear_state=True, log_event=True)
handler = metrics.log_metrics(handler, capture_cold_start_metric=True)


class ErrorResponse(CamelModel):
    status: int
    id: uuid.UUID
    message: str


class ValidationErrorResponse(ErrorResponse):
    errors: List[Dict]


@app.post('/api/v1/login', status_code=status.HTTP_200_OK)
async def login(body: Login) -> Token:
    jwt_token = await auth_service.login(body.email, body.password)
    metrics.add_metric(name='Login', unit=MetricUnit.Count, value=1)
    return jwt_token


@app.get(
    '/api/v1/logout',
    dependencies=[Depends(jwt_bearer)],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout():
    await auth_service.logout(jwt_bearer.decoded_token)
    metrics.add_metric(name='Logout', unit=MetricUnit.Count, value=1)


async def botocore_error_handler(
    request: Request, error: BotoCoreError
) -> JSONResponse:
    error_id = uuid.uuid4()
    error_message = str(error) if settings.app_debug else 'Internal Server Error'
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    logger.error(f'{str(error)} with {status_code=} and {error_id=}')
    metrics.add_metric(name='BotocoreErrorHandler', unit=MetricUnit.Count, value=1)
    return JSONResponse(
        content=jsonable_encoder(
            ErrorResponse(status=status_code, id=error_id, message=error_message)
        ),
        status_code=status_code,
    )


for k, v in sorted(
    filter(
        lambda elem: isclass(elem[1]) and issubclass(elem[1], BotoCoreError),
        botocore.exceptions.__dict__.items(),
    )
):
    app.add_exception_handler(v, botocore_error_handler)


@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request, error: HTTPException
) -> JSONResponse:
    error_id = uuid.uuid4()
    logger.error(f'{error.detail} with {error.status_code=} and {error_id=}')
    metrics.add_metric(name='HttpExceptionHandler', unit=MetricUnit.Count, value=1)
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
    error_message = str(error)
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    logger.error(f'{error_message} with {status_code=} and {error_id=}')
    metrics.add_metric(
        name='RequestValidationErrorHandler', unit=MetricUnit.Count, value=1
    )
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


if __name__ == '__main__':
    uvicorn.run('app.main:app', host='localhost', port=3000, reload=True)
