import secrets
import uuid
from typing import Any, Tuple

import jwt
import pendulum
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerifyMismatchError
from aws_lambda_powertools import Logger
from fastapi import HTTPException, status

from app import settings
from app.exceptions import (
    TokenMismatchException,
    TokenNotFoundException,
    UserNotFoundException,
)
from app.models import JWTToken, User
from app.repositories import TokenRepository, UserRepository

logger = Logger(utc=True)

ERROR_MESSAGE_INTERNAL_SERVER_ERROR = "Internal Server Error"
ERROR_MESSAGE_TOKEN_NOT_FOUND = "The requested token was not found"
ERROR_MESSAGE_UNAUTHORIZED = "Unauthorized"
ERROR_MESSAGE_USER_NOT_FOUND = "The requested user was not found"
X_API_KEY = "X-Api-Key"
X_CORRELATION_ID = "X-Correlation-ID"


class AuthService:
    def __init__(self):
        self._password_hasher = PasswordHasher()
        self._token_service = TokenService()
        self._user_repository = UserRepository()

    def _generate_token(
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

    def _generate_refresh_token(self, length: int = 16):
        return secrets.token_hex(length)

    def _generate_tokens_for_user(
        self,
        jwt_token: JWTToken,
    ) -> tuple[JWTToken, str]:
        logger.info(
            f"Generate new tokens for user={jwt_token.user['id']}",
            extra={"user": jwt_token.user},
        )
        jwt_token = self._generate_token(
            jwt_token.sub, settings.jwt_token_lifetime, jwt_token.user
        )
        refresh_token = self._generate_refresh_token()
        self._token_service.create(jwt_token, refresh_token)
        return jwt_token, refresh_token

    def _revoke_token(self, jwt_token: JWTToken):
        logger.info(
            f"Revoking token with jti={jwt_token.jti}", extra={"jwt_token": jwt_token}
        )
        self._token_service.delete_by_id(jwt_token.jti)

    def login(self, email: str, password: str) -> tuple[str, str]:
        user = self._user_repository.get_by_email(email)
        if user is None:
            raise UserNotFoundException(ERROR_MESSAGE_USER_NOT_FOUND)
        try:
            self._password_hasher.verify(user.password, password)
            jwt_token = self._generate_token(user.id, user=user)
            refresh_token = self._generate_refresh_token()
            self._token_service.create(jwt_token, refresh_token)
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

    def logout(self, jwt_token: JWTToken):
        self._token_service.delete_by_id(jwt_token.jti)

    def refresh(self, jwt_token: JWTToken, refresh_token: str) -> tuple[str, str]:
        item = self._token_service.get_by_refresh_token(refresh_token)
        if item is None:
            logger.warning("The requested token was not found!")
            raise TokenNotFoundException(ERROR_MESSAGE_TOKEN_NOT_FOUND)
        if jwt_token.model_dump() != item["jwt_token"]:
            raise TokenMismatchException("Internal Server Error")
        self._revoke_token(jwt_token)
        jwt_token, refresh_token = self._generate_tokens_for_user(jwt_token)
        return (
            jwt.encode(jwt_token.model_dump(exclude_none=True), settings.jwt_secret),
            refresh_token,
        )


class TokenService:
    def __init__(self):
        self._token_repository = TokenRepository()

    def create(self, jwt_token: JWTToken, refresh_token: str):
        now = pendulum.now()
        self._token_repository.create_token(
            {
                "jti": jwt_token.jti,
                "jwt_token": jwt_token.model_dump(),
                "refresh_token": refresh_token,
                "created_at": now.to_iso8601_string(),
                "ttl": jwt_token.exp,
            }
        )

    def delete_by_id(self, jti: str):
        response = self._token_repository.delete_by_id(jti)
        if response["ResponseMetadata"]["HTTPStatusCode"] != status.HTTP_200_OK:
            raise TokenNotFoundException(ERROR_MESSAGE_TOKEN_NOT_FOUND)

    def get_by_id(self, jti: str) -> Tuple[JWTToken, str] | None:
        return self._token_repository.get_by_id(jti)

    def get_by_refresh_token(self, refresh_token: str) -> dict[str, Any] | None:
        return self._token_repository.get_by_refresh_token(refresh_token)
