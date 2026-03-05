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
    OAuthException,
    TokenExpiredException,
    TokenMismatchException,
    TokenNotFoundException,
    UserNotFoundException,
)
from app.models.jwt import JWTToken, RefreshToken
from app.models.user import User
from app.repositories.service_repository import ServiceRepository
from app.repositories.user_repository import UserRepository
from app.services.token_service import TokenService

ERROR_MESSAGE_UNAUTHORIZED = "Unauthorized"
ERROR_MESSAGE_TOKEN_NOT_FOUND = "The requested token was not found"
ERROR_MESSAGE_USER_NOT_FOUND = "The requested user was not found"

ROLE_SCOPE_MAP: dict[str, list[str]] = {
    "root": ["tokens:revoke", "users:read", "users:write"],
}


class AuthService:
    def __init__(self):
        self._logger = Logger()
        self._password_hasher = PasswordHasher()
        self._service_repository = ServiceRepository()
        self._token_service = TokenService()
        self._user_repository = UserRepository()

    def _derive_scope(
        self, roles: list[str], requested_scope: str | None
    ) -> str | None:
        allowed_scopes: set[str] = set()
        for role in roles:
            allowed_scopes.update(ROLE_SCOPE_MAP.get(role, []))

        if not allowed_scopes:
            return None

        if requested_scope:
            requested = set(requested_scope.split())
            if not requested.issubset(allowed_scopes):
                raise OAuthException("invalid_scope")
            return requested_scope

        return " ".join(sorted(allowed_scopes))

    def _generate_token(
        self,
        sub: str,
        user: dict[str, Any] | User | None,
        exp: int | None = None,
        scope: str | None = None,
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
            iss=settings.jwt_issuer if settings.jwt_issuer else None,
            jti=str(uuid.uuid4()),
            sub=sub,
            scope=scope,
            user=user,
        )

    def _generate_refresh_token(self, length: int = 16):
        return secrets.token_hex(length)

    def _generate_tokens_for_user(
        self,
        user: dict[str, Any],
        scope: str | None = None,
    ) -> tuple[JWTToken, RefreshToken]:
        self._logger.info(
            f"Generate new tokens for user={user['id']}",
            extra={"user": user},
        )

        jwt_token = self._generate_token(
            user["id"], user, settings.jwt_token_lifetime, scope=scope
        )
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

    def login(
        self, username: str, password: str, requested_scope: str | None = None
    ) -> tuple[str, str, int, str | None]:
        user = self._user_repository.get_by_email(username)

        if user is None:
            raise UserNotFoundException(ERROR_MESSAGE_USER_NOT_FOUND)
        try:
            self._password_hasher.verify(user.password, password)

            scope = self._derive_scope(user.roles, requested_scope)
            user_dict = user.model_dump(
                exclude={"password", "created_at", "deleted_at", "updated_at"}
            )
            jwt_token, refresh_token = self._generate_tokens_for_user(
                user_dict, scope=scope
            )

            return (
                jwt.encode(
                    jwt_token.model_dump(exclude_none=True), settings.jwt_secret
                ),
                refresh_token.token,
                settings.jwt_token_lifetime,
                scope,
            )
        except (InvalidHash, VerifyMismatchError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGE_UNAUTHORIZED,
            )

    def logout(self, jwt_token: JWTToken):
        self._revoke_token(jwt_token)

    def refresh(
        self, jwt_token: JWTToken, refresh_token: str
    ) -> tuple[str, str, int, str | None]:
        item = self._token_service.get_by_refresh_token(refresh_token)

        if item is None:
            self._logger.warning("The requested token was not found!")
            raise TokenNotFoundException(ERROR_MESSAGE_TOKEN_NOT_FOUND)

        if jwt_token.model_dump() != item["jwt_token"]:
            raise TokenMismatchException("Internal Server Error")

        if item["ttl"] < pendulum.now().int_timestamp:
            raise TokenExpiredException("The requested token has expired")

        self._revoke_token(jwt_token)

        scope = item["jwt_token"].get("scope")
        jwt_token, refresh_token = self._generate_tokens_for_user(
            item["jwt_token"]["user"], scope=scope
        )

        return (
            jwt.encode(jwt_token.model_dump(exclude_none=True), settings.jwt_secret),
            refresh_token.token,
            settings.jwt_token_lifetime,
            scope,
        )

    def client_credentials(
        self, client_id: str, client_secret: str, requested_scope: str | None
    ) -> tuple[str, int, str | None]:
        service = self._service_repository.get_by_id(client_id)
        if service is None:
            raise OAuthException(
                "invalid_client",
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": "Basic"},
            )
        try:
            self._password_hasher.verify(service.secret, client_secret)
        except (InvalidHash, VerifyMismatchError):
            raise OAuthException(
                "invalid_client",
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": "Basic"},
            )

        allowed = set(service.scopes)
        if requested_scope:
            requested = set(requested_scope.split())
            if not requested.issubset(allowed):
                raise OAuthException("invalid_scope")
            granted_scope = requested_scope
        else:
            granted_scope = " ".join(sorted(allowed)) if allowed else None

        jwt_token = self._generate_token(
            sub=client_id,
            user=None,
            exp=settings.jwt_token_lifetime,
            scope=granted_scope,
        )
        self._token_service.create(
            jwt_token,
            RefreshToken(
                token=self._generate_refresh_token(),
                ttl=jwt_token.iat + settings.jwt_token_lifetime,
            ),
        )

        encoded = jwt.encode(
            jwt_token.model_dump(exclude_none=True), settings.jwt_secret
        )
        return encoded, settings.jwt_token_lifetime, granted_scope
