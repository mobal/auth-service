import uuid
from typing import Any, Tuple

import httpx
import jwt
import pendulum
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerifyMismatchError
from aws_lambda_powertools import Logger
from fastapi import HTTPException, status

from app import settings
from app.exceptions import CacheServiceException, UserNotFoundException
from app.middlewares import correlation_id
from app.models import JWTToken
from app.repositories import TokenRepository, UserRepository

logger = Logger(utc=True)

ERROR_MESSAGE_INTERNAL_SERVER_ERROR = "Internal Server Error"
ERROR_MESSAGE_USER_NOT_FOUND = "The requested user was not found"
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
                    X_API_KEY: settings.cache_service_api_key,
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
                    X_API_KEY: settings.cache_service_api_key,
                },
                json={"key": key, "value": value, "ttl": ttl},
            )
        if response.status_code == status.HTTP_201_CREATED:
            logger.info(f"Cache successfully created {key=} {value=} {ttl=}")
        else:
            logger.error(f"Failed to put cache {key=} {value=} {ttl=}")
            raise CacheServiceException(detail=ERROR_MESSAGE_INTERNAL_SERVER_ERROR)


class AuthService:
    def __init__(self):
        self.__cache_service = CacheService()
        self.__password_hasher = PasswordHasher()
        self.__token_service = TokenService()
        self.__user_repository = UserRepository()

    async def __generate_token(self, payload: dict, exp: int | None = None) -> JWTToken:
        iat = pendulum.now()
        exp = (
            iat.add(seconds=settings.jwt_token_lifetime)
            if exp is None
            else iat.add(seconds=exp)
        )
        return JWTToken(
            exp=exp.int_timestamp,
            iat=iat.int_timestamp,
            jti=str(uuid.uuid4()),
            sub=payload,
        )

    async def login(self, email: str, password: str) -> (str, str):
        user = await self.__user_repository.get_by_email(email)
        if user is None:
            raise UserNotFoundException(ERROR_MESSAGE_USER_NOT_FOUND)
        try:
            self.__password_hasher.verify(user.password, password)
            jwt_token = await self.__generate_token(
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
            refresh_token = await self.__generate_token(
                {"jti": jwt_token.jti}, settings.refresh_token_lifetime
            )
            await self.__token_service.create(jwt_token, refresh_token)
            return jwt.encode(jwt_token.model_dump(), settings.jwt_secret), jwt.encode(
                refresh_token.model_dump(), settings.jwt_secret
            )
        except (InvalidHash, VerifyMismatchError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized",
            )

    async def logout(self, jwt_token: JWTToken):
        await self.__cache_service.put(
            f"jti_{jwt_token.jti}", jwt_token.model_dump(), jwt_token.exp
        )


class TokenService:
    def __init__(self):
        self.__token_repository = TokenRepository()

    async def create(self, jwt_token: JWTToken, refresh_token: JWTToken):
        await self.__token_repository.create_token(
            {
                "jti": jwt_token.jti,
                "jwt_token": jwt_token.model_dump(),
                "refresh_token": refresh_token.model_dump(),
                "ttl": jwt_token.exp,
            }
        )

    async def delete(self, jti: str):
        await self.__token_repository.delete_by_id(jti)

    async def get_by_id(self, jti: str) -> Tuple[JWTToken, JWTToken]:
        item = await self.__token_repository.get_token_by_id(jti)
        return JWTToken(**item["jwt_token"]), JWTToken(**item["refresh_token"])
