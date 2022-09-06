import logging
import uuid
from typing import Optional, Any
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerifyMismatchError

import httpx
import jwt
import pendulum
from fastapi import HTTPException
from fastapi_camelcase import CamelModel
from pydantic.main import BaseModel
from pydantic.networks import EmailStr
from starlette import status

from app.exceptions import CacheServiceException, UserNotFoundException
from app.repositories import UserRepository
from app.settings import Settings


class Cache(CamelModel):
    key: str
    value: Any
    created_at: str
    ttl: int


class JWTToken(BaseModel):
    exp: int
    iat: int
    iss: Optional[str]
    jti: str
    sub: Any


class User(CamelModel):
    id: str
    display_name: str
    email: EmailStr
    password: str
    roles: list[str]
    username: str
    created_at: str
    deleted_at: Optional[str]
    updated_at: Optional[str]


class Token(CamelModel):
    token: str


class CacheService:
    ERROR_MESSAGE_INTERNAL_SERVER_ERROR = 'Internal Server Error'

    def __init__(self):
        self._logger = logging.getLogger()
        self.settings = Settings()

    async def get(self, key: str) -> Optional[Cache]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'{self.settings.cache_service_base_url}/api/cache/{key}'
            )
        if response.status_code == status.HTTP_200_OK:
            return Cache.parse_obj(response.json())
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            return None
        self._logger.error(f'Failed to get cache {response=}')
        raise CacheServiceException(detail=self.ERROR_MESSAGE_INTERNAL_SERVER_ERROR)

    async def put(self, key: str, value: Any, ttl: int = 0):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f'{self.settings.cache_service_base_url}/api/cache',
                json={'key': key, 'value': value, 'ttl': ttl},
            )
        if response.status_code == status.HTTP_201_CREATED:
            self._logger.info(f'Cache successfully created {key=} {value=} {ttl=}')
        else:
            self._logger.error(f'Failed to put cache {key=} {value=} {ttl=}')
            raise CacheServiceException(detail=self.ERROR_MESSAGE_INTERNAL_SERVER_ERROR)


class AuthService:
    ERROR_MESSAGE_USER_NOT_FOUND = 'The requested user was not found'

    def __init__(self):
        self._logger = logging.getLogger()
        self.cache_service = CacheService()
        self.password_hasher = PasswordHasher()
        self.settings = Settings()
        self.user_repository = UserRepository()

    async def _generate_token(self, payload: dict) -> str:
        iat = pendulum.now()
        exp = iat.add(seconds=self.settings.jwt_token_lifetime)
        return jwt.encode(
            JWTToken(
                exp=exp.int_timestamp,
                iat=iat.int_timestamp,
                jti=str(uuid.uuid4()),
                sub=payload,
            ).dict(),
            self.settings.jwt_secret,
        )

    async def login(self, email: str, password: str) -> Token:
        item = await self.user_repository.get_by_email(email)
        if item is None:
            raise UserNotFoundException(self.ERROR_MESSAGE_USER_NOT_FOUND)
        try:
            self.password_hasher.verify(item['password'], password)
            del item['password']
            return Token(token=await self._generate_token(item))
        except (InvalidHash, VerifyMismatchError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Unauthorized',
            )

    async def logout(self, jwt_token: JWTToken):
        await self.cache_service.put(
            f'jti_{jwt_token.jti}', jwt_token.dict(), jwt_token.exp
        )
