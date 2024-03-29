import uuid
from typing import Any, Optional

import httpx
import jwt
import pendulum
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerifyMismatchError
from aws_lambda_powertools import Logger
from fastapi import HTTPException
from humps import camelize
from pydantic import ConfigDict
from pydantic.main import BaseModel
from pydantic.networks import EmailStr
from starlette import status

from app.exceptions import CacheServiceException, UserNotFoundException
from app.middlewares import correlation_id
from app.repositories import UserRepository
from app.settings import Settings

logger = Logger(utc=True)


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=camelize, populate_by_name=True)


class Cache(CamelModel):
    key: str
    value: Any
    created_at: str
    ttl: int


class JWTToken(BaseModel):
    exp: int
    iat: int
    iss: Optional[str] = None
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
    deleted_at: Optional[str] = None
    updated_at: Optional[str] = None


class Token(CamelModel):
    token: str


class CacheService:
    ERROR_MESSAGE_INTERNAL_SERVER_ERROR = "Internal Server Error"
    X_CORRELATION_ID = "X-Correlation-ID"

    def __init__(self):
        self._settings = Settings()

    async def get(self, key: str) -> bool:
        async with httpx.AsyncClient() as client:
            url = f"{self._settings.cache_service_base_url}/api/cache/{key}"
            logger.debug(f"Get cache for {key=} {url=}")
            response = await client.get(
                url, headers={self.X_CORRELATION_ID: correlation_id.get()}
            )
        if response.is_success:
            return True
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            logger.debug(f"Cache was not found for {key=}")
            return False
        logger.error(f"Unexpected error {response=}")
        raise CacheServiceException(detail=self.ERROR_MESSAGE_INTERNAL_SERVER_ERROR)

    async def put(self, key: str, value: Any, ttl: int = 0):
        async with httpx.AsyncClient() as client:
            url = f"{self._settings.cache_service_base_url}/api/cache"
            response = await client.post(
                url,
                headers={self.X_CORRELATION_ID: correlation_id.get()},
                json={"key": key, "value": value, "ttl": ttl},
            )
        if response.status_code == status.HTTP_201_CREATED:
            logger.info(f"Cache successfully created {key=} {value=} {ttl=}")
        else:
            logger.error(f"Failed to put cache {key=} {value=} {ttl=}")
            raise CacheServiceException(detail=self.ERROR_MESSAGE_INTERNAL_SERVER_ERROR)


class AuthService:
    ERROR_MESSAGE_USER_NOT_FOUND = "The requested user was not found"

    def __init__(self):
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
            ).model_dump(),
            self.settings.jwt_secret,
        )

    async def login(self, email: str, password: str) -> Token:
        item = await self.user_repository.get_by_email(email)
        if item is None:
            raise UserNotFoundException(self.ERROR_MESSAGE_USER_NOT_FOUND)
        try:
            self.password_hasher.verify(item["password"], password)
            del item["password"]
            return Token(token=await self._generate_token(item))
        except (InvalidHash, VerifyMismatchError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized",
            )

    async def logout(self, jwt_token: JWTToken):
        await self.cache_service.put(
            f"jti_{jwt_token.jti}", jwt_token.model_dump(), jwt_token.exp
        )
