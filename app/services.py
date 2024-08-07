import uuid
from typing import Any

import httpx
import jwt
import pendulum
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerifyMismatchError
from aws_lambda_powertools import Logger
from fastapi import HTTPException
from starlette import status

from app import settings
from app.exceptions import CacheServiceException, UserNotFoundException
from app.middlewares import correlation_id
from app.models import JWTToken, Token
from app.repositories import UserRepository

logger = Logger(utc=True)

ERROR_MESSAGE_INTERNAL_SERVER_ERROR = "Internal Server Error"
X_API_KEY = "X-Api-Key"
X_CORRELATION_ID = "X-Correlation-ID"


class CacheService:
    async def get(self, key: str) -> bool:
        async with httpx.AsyncClient() as client:
            url = f"{settings.cache_service_base_url}/api/cache/{key}"
            logger.debug(f"Get cache for {key=} {url=}")
            response = await client.get(
                url,
                headers={
                    X_CORRELATION_ID: correlation_id.get(),
                    X_API_KEY: settings.x_api_key,
                },
            )
        if response.is_success:
            return True
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            logger.debug(f"Cache was not found for {key=}")
            return False
        logger.error(f"Unexpected error {response=}")
        raise CacheServiceException(detail=ERROR_MESSAGE_INTERNAL_SERVER_ERROR)

    async def put(self, key: str, value: Any, ttl: int = 0):
        async with httpx.AsyncClient() as client:
            url = f"{settings.cache_service_base_url}/api/cache"
            response = await client.post(
                url,
                headers={
                    X_CORRELATION_ID: correlation_id.get(),
                    X_API_KEY: settings.x_api_key,
                },
                json={"key": key, "value": value, "ttl": ttl},
            )
        if response.status_code == status.HTTP_201_CREATED:
            logger.info(f"Cache successfully created {key=} {value=} {ttl=}")
        else:
            logger.error(f"Failed to put cache {key=} {value=} {ttl=}")
            raise CacheServiceException(detail=ERROR_MESSAGE_INTERNAL_SERVER_ERROR)


class AuthService:
    ERROR_MESSAGE_USER_NOT_FOUND = "The requested user was not found"

    def __init__(self):
        self.cache_service = CacheService()
        self.password_hasher = PasswordHasher()
        self.user_repository = UserRepository()

    async def __generate_token(self, payload: dict) -> str:
        iat = pendulum.now()
        exp = iat.add(seconds=settings.jwt_token_lifetime)
        return jwt.encode(
            JWTToken(
                exp=exp.int_timestamp,
                iat=iat.int_timestamp,
                jti=str(uuid.uuid4()),
                sub=payload,
            ).model_dump(),
            settings.jwt_secret,
        )

    async def login(self, email: str, password: str) -> Token:
        user = await self.user_repository.get_by_email(email)
        if user is None:
            raise UserNotFoundException(self.ERROR_MESSAGE_USER_NOT_FOUND)
        try:
            self.password_hasher.verify(user.password, password)
            return Token(
                token=await self.__generate_token(
                    user.model_dump(
                        exclude={
                            "id",
                            "created_at",
                            "deleted_at",
                            "password",
                            "updated_at",
                        },
                    )
                )
            )
        except (InvalidHash, VerifyMismatchError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized",
            )

    async def logout(self, jwt_token: JWTToken):
        await self.cache_service.put(
            f"jti_{jwt_token.jti}", jwt_token.model_dump(), jwt_token.exp
        )
