import secrets
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
from app.exceptions import (
    CacheServiceException,
    TokenMistmatchException,
    TokenNotFoundException,
    UserNotFoundException,
)
from app.middlewares import correlation_id
from app.models import JWTToken, User
from app.repositories import TokenRepository, UserRepository

logger = Logger(utc=True)

ERROR_MESSAGE_INTERNAL_SERVER_ERROR = "Internal Server Error"
ERROR_MESSAGE_TOKEN_NOT_FOUND = "The requested token was not found"
ERROR_MESSAGE_UNAUTHORIZED = "Unauthorized"
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
        self._cache_service = CacheService()
        self._password_hasher = PasswordHasher()
        self._token_service = TokenService()
        self._user_repository = UserRepository()

    async def _generate_token(
        self,
        sub: str,
        exp: int | None = None,
        user: dict[str, Any] | User | None = None,
    ) -> JWTToken:
        iat = pendulum.now()
        exp = (
            iat.add(seconds=settings.jwt_token_lifetime)
            if exp is None
            else iat.add(seconds=exp)
        )
        if user and isinstance(user, User):
            user = user.model_dump(
                exclude={"password", "created_at", "deleted_at", "updated_at"}
            )
        return JWTToken(
            exp=exp.int_timestamp,
            iat=iat.int_timestamp,
            jti=str(uuid.uuid4()),
            sub=sub,
            user=user,
        )

    async def _generate_refresh_token(self, length: int = 16):
        return secrets.token_hex(length)

    async def _generate_tokens_for_user(
        self,
        jwt_token: JWTToken,
    ) -> tuple[JWTToken, str]:
        logger.info(
            f"Generate new tokens for user={jwt_token.user["id"]}",
            extra={"user": jwt_token.user},
        )
        jwt_token = await self._generate_token(
            jwt_token.sub, settings.jwt_token_lifetime, jwt_token.user
        )
        refresh_token = await self._generate_refresh_token()
        await self._token_service.create(jwt_token, refresh_token)
        return jwt_token, refresh_token

    async def _revoke_token(self, jwt_token: JWTToken):
        logger.info(
            f"Revoking token with jti={jwt_token.jti}", extra={"jwt_token": jwt_token}
        )
        await self._token_service.delete_by_id(jwt_token.jti)
        await self._cache_service.put(
            f"jti_{jwt_token.jti}", jwt_token.model_dump(), jwt_token.exp
        )

    async def login(self, email: str, password: str) -> tuple[str, str]:
        user = await self._user_repository.get_by_email(email)
        if user is None:
            raise UserNotFoundException(ERROR_MESSAGE_USER_NOT_FOUND)
        try:
            self._password_hasher.verify(user.password, password)
            jwt_token = await self._generate_token(user.id, user=user)
            refresh_token = await self._generate_refresh_token()
            await self._token_service.create(jwt_token, refresh_token)
            return (
                jwt.encode(
                    jwt_token.model_dump(exclude_none=True), settings.jwt_secret
                ),
                refresh_token,
            )
        except (InvalidHash, VerifyMismatchError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGE_UNAUTHORIZED,
            )

    async def logout(self, jwt_token: JWTToken):
        await self._cache_service.put(
            f"jti_{jwt_token.jti}", jwt_token.model_dump(), jwt_token.exp
        )
        await self._token_service.delete_by_id(jwt_token.jti)

    async def refresh(
        self, jwt_token: JWTToken, refresh_token: str
    ) -> tuple[JWTToken, str]:
        item = await self._token_service.get_by_refresh_token(refresh_token)
        if item is None:
            logger.warning("The requested token was not found!")
            raise TokenNotFoundException(ERROR_MESSAGE_TOKEN_NOT_FOUND)
        if jwt_token.model_dump() != item["jwt_token"]:
            raise TokenMistmatchException("Internal Server Error")
        await self._revoke_token(jwt_token)
        jwt_token, refresh_token = await self._generate_tokens_for_user(jwt_token)
        return (
            jwt.encode(jwt_token.model_dump(exclude_none=True), settings.jwt_secret),
            refresh_token,
        )


class TokenService:
    def __init__(self):
        self._token_repository = TokenRepository()

    async def create(self, jwt_token: JWTToken, refresh_token: str):
        now = pendulum.now()
        await self._token_repository.create_token(
            {
                "jti": jwt_token.jti,
                "jwt_token": jwt_token.model_dump(),
                "refresh_token": refresh_token,
                "created_at": now.to_iso8601_string(),
                "ttl": jwt_token.exp,
            }
        )

    async def delete_by_id(self, jti: str):
        response = await self._token_repository.delete_by_id(jti)
        if response["ResponseMetadata"]["HTTPStatusCode"] != status.HTTP_200_OK:
            raise TokenNotFoundException(ERROR_MESSAGE_TOKEN_NOT_FOUND)

    async def get_by_id(self, jti: str) -> Tuple[JWTToken, JWTToken] | None:
        return await self._token_repository.get_by_id(jti)

    async def get_by_refresh_token(self, refresh_token: str) -> dict[str, Any]:
        return await self._token_repository.get_by_refresh_token(refresh_token)
