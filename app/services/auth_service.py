import secrets
import uuid
from typing import Any

import jwt
import pendulum
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerifyMismatchError
from aws_lambda_powertools import Logger
from fastapi import HTTPException
from starlette import status

from app import settings
from app.exceptions import (
    TokenExpiredException,
    TokenMismatchException,
    TokenNotFoundException,
    UserNotFoundException,
)
from app.models.jwt import JWTToken, RefreshToken
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.token_service import TokenService

ERROR_MESSAGE_UNAUTHORIZED = "Unauthorized"
ERROR_MESSAGE_TOKEN_NOT_FOUND = "The requested token was not found"
ERROR_MESSAGE_USER_NOT_FOUND = "The requested user was not found"


class AuthService:
    def __init__(self):
        self._logger = Logger()
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
        user: dict[str, Any],
    ) -> tuple[JWTToken, RefreshToken]:
        self._logger.info(
            f"Generate new tokens for user={user['id']}",
            extra={"user": user},
        )

        jwt_token = self._generate_token(user["id"], settings.jwt_token_lifetime, user)
        refresh_token = RefreshToken(
            token=self._generate_refresh_token(),
            ttl=jwt_token.iat + settings.refresh_token_lifetime,
        )
        self._token_service.create(jwt_token, refresh_token)

        return jwt_token, refresh_token

    def _revoke_token(self, jwt_token: JWTToken):
        self._logger.info(
            f"Revoking token with jti={jwt_token.jti}", extra={"jwt_token": jwt_token}
        )
        self._token_service.delete_by_id(jwt_token.jti)

    def login(self, email: str, password: str) -> tuple[str, str, int]:
        user = self._user_repository.get_by_email(email)

        if user is None:
            raise UserNotFoundException(ERROR_MESSAGE_USER_NOT_FOUND)
        try:
            self._password_hasher.verify(user.password, password)

            jwt_token, refresh_token = self._generate_tokens_for_user(
                user.model_dump(
                    exclude={"password", "created_at", "deleted_at", "updated_at"}
                )
            )

            return (
                jwt.encode(
                    jwt_token.model_dump(exclude_none=True), settings.jwt_secret
                ),
                refresh_token.token,
                settings.jwt_token_lifetime,
            )
        except (InvalidHash, VerifyMismatchError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGE_UNAUTHORIZED,
            )

    def logout(self, jwt_token: JWTToken):
        self._token_service.delete_by_id(jwt_token.jti)

    def refresh(self, jwt_token: JWTToken, refresh_token: str) -> tuple[str, str, int]:
        item = self._token_service.get_by_refresh_token(refresh_token)

        if item is None:
            self._logger.warning("The requested token was not found!")
            raise TokenNotFoundException(ERROR_MESSAGE_TOKEN_NOT_FOUND)

        if jwt_token.model_dump() != item["jwt_token"]:
            raise TokenMismatchException("Internal Server Error")

        if item["refresh_token_ttl"] < pendulum.now().int_timestamp:
            raise TokenExpiredException("The requested token has expired")

        self._revoke_token(jwt_token)

        jwt_token, refresh_token = self._generate_tokens_for_user(
            item["jwt_token"]["user"]
        )

        return (
            jwt.encode(jwt_token.model_dump(exclude_none=True), settings.jwt_secret),
            refresh_token.token,
            settings.jwt_token_lifetime,
        )
