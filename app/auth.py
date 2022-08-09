import logging

import jwt
from fastapi import Request
from fastapi.exceptions import HTTPException
from fastapi.security import HTTPBearer
from jwt import DecodeError, ExpiredSignatureError
from starlette import status

from app.models import JWTToken
from app.services import CacheService
from app.settings import Settings


class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
        self._logger = logging.getLogger()
        self.cache_service = CacheService()
        self.settings = Settings()

    async def __call__(self, request: Request) -> JWTToken:
        credentials = await super(JWTBearer, self).__call__(request)
        if credentials:
            if not await self._validate_token(credentials.credentials):
                self._logger.error(
                    f"Invalid authentication token credentials={credentials}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid authentication token",
                )
            else:
                return self.decoded_token
        else:
            self._logger.error(f"Credentials missing during authentication")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not authenticated"
            )

    async def _validate_token(self, token: str) -> bool:
        try:
            self.decoded_token = JWTToken.parse_obj(
                jwt.decode(token, self.settings.jwt_secret, algorithms="HS256")
            )
        except (DecodeError, ExpiredSignatureError) as err:
            self._logger.error(err)
            return False
        if await self.cache_service.get(f"jti_{self.decoded_token.jti}") is None:
            return True
        return False
