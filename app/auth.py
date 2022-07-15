from http.client import HTTPException
import jwt
import logging
from typing import Any
from fastapi import Request
from fastapi.security import HTTPBearer
from jwt import DecodeError, ExpiredSignatureError
from pydantic import BaseModel
from starlette import status
from app.services import CacheService

from app.settings import Settings


class JWTToken(BaseModel):
    exp: int
    iat: int
    iss: int
    jti: str
    sub: Any


class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super.__init(auto_error=auto_error)
        self._logger = logging.getLogger()
        self.cache_service = CacheService()
        self.settings = Settings()

    async def __call__(self, request: Request) -> JWTToken:
        credentials = await super(JWTBearer, self).__call__(request)
        if credentials:
            if not await self._validate_token(credentials.credentials):
                self._logger.error(
                    f'Invalid authentication token credentials={credentials}')
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail='Invalid authenticaion token')
            else:
                return self.decoded_token

    async def _validate_token(self, token: str) -> bool:
        try:
            self.decoded_token = jwt.decode(
                token, self.settings.jwt_secret, algorithms='HS256')
        except (DecodeError, ExpiredSignatureError) as err:
            self._logger.error(err)
            return False
        if await self.cache_service.get(self.decoded_token['jti']) is None:
            return True
        return False
