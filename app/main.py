import logging
import uuid
from typing import List, Dict

import uvicorn
from botocore.exceptions import ClientError
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi_camelcase import CamelModel
from mangum import Mangum
from pydantic import ValidationError
from starlette import status
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from app.auth import JWTBearer
from app.models import Token
from app.schemas import Login
from app.services import AuthService

logger = logging.getLogger()

app = FastAPI()
auth_service = AuthService()
jwt_bearer = JWTBearer()


@app.post('/api/v1/login', status_code=status.HTTP_200_OK)
async def login(body: Login) -> Token:
    return await auth_service.login(body.email, body.password)


@app.get('/api/v1/logout', dependencies=[Depends(jwt_bearer)],
         status_code=status.HTTP_204_NO_CONTENT)
async def logout():
    await auth_service.logout(jwt_bearer.decoded_token)


handler = Mangum(app)


class ErrorResponse(CamelModel):
    status: int
    id: uuid.UUID
    message: str


class ValidationErrorResponse(ErrorResponse):
    errors: List[Dict]


@app.exception_handler(ClientError)
async def client_error_handler(request: Request, error: ClientError) -> JSONResponse:
    error_id = uuid.uuid4()
    error_message = str(error)
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    logger.error(
        f'{error_message} with status_code={status_code}, error_id={error_id}')
    return JSONResponse(
        content=jsonable_encoder(ErrorResponse(
            status=status_code, id=error_id, message=error_message)),
        status_code=status_code
    )


@app.exception_handler(HTTPException)
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, error: HTTPException) -> JSONResponse:
    error_id = uuid.uuid4()
    logger.error(
        f'{error.detail} with status_code={error.status_code}, error_id={error_id}')
    return JSONResponse(
        content=jsonable_encoder(ErrorResponse(
            status=error.status_code, id=error_id, message=error.detail)),
        status_code=error.status_code
    )


@app.exception_handler(RequestValidationError)
@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, error: ValidationError) -> JSONResponse:
    error_id = uuid.uuid4()
    error_message = str(error)
    status_code = status.HTTP_400_BAD_REQUEST
    logger.error(
        f'{error_message} with status_code={status_code}, error_id={error_id}')
    return JSONResponse(
        content=jsonable_encoder(
            ValidationErrorResponse(
                status=status_code,
                id=error_id,
                message=str(error),
                errors=error.errors())),
        status_code=status_code)


if __name__ == '__main__':
    uvicorn.run('app.main:app', host='localhost', port=3000, reload=True)
