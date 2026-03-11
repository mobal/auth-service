import base64
import hashlib
import secrets
import uuid

import jwt
import pendulum
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerifyMismatchError
from aws_lambda_powertools import Logger
from starlette import status

from app import settings
from app.clients.user_service_client import UserServiceClient
from app.exceptions import (
    InvalidCredentialsException,
    OAuthException,
    TokenExpiredException,
    TokenNotFoundException,
    UserNotFoundException,
)
from app.models.authorization_code import AuthorizationCode
from app.models.jwt import JWTToken, RefreshToken
from app.repositories.authorization_code_repository import AuthorizationCodeRepository
from app.repositories.service_repository import ServiceRepository
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
        self._authorization_code_repository = AuthorizationCodeRepository()
        self._service_repository = ServiceRepository()
        self._token_service = TokenService()
        self._user_service_client = UserServiceClient()

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

    @staticmethod
    def _get_pkce_challenge(
        code_verifier: str,
        code_challenge_method: str | None,
    ) -> str:
        if code_challenge_method == "S256":
            return (
                base64.urlsafe_b64encode(
                    hashlib.sha256(code_verifier.encode()).digest()
                )
                .decode()
                .rstrip("=")
            )

        if code_challenge_method == "plain":
            return code_verifier

        raise OAuthException(
            "invalid_request",
            "Unsupported code_challenge_method",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    def _validate_pkce(
        self,
        auth_code: AuthorizationCode,
        code_verifier: str | None,
    ):
        if not auth_code.code_challenge:
            return

        if not code_verifier:
            raise OAuthException(
                "invalid_request",
                "Missing code_verifier",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        expected_challenge = self._get_pkce_challenge(
            code_verifier,
            auth_code.code_challenge_method,
        )
        if expected_challenge != auth_code.code_challenge:
            raise OAuthException(
                "invalid_grant", status_code=status.HTTP_400_BAD_REQUEST
            )

    def _generate_token(
        self,
        sub: str,
        exp: int | None = None,
        scope: str | None = None,
    ) -> JWTToken:
        iat = pendulum.now()
        exp = (
            iat.add(seconds=settings.jwt_token_lifetime)
            if exp is None
            else iat.add(seconds=exp)
        )

        return JWTToken(
            exp=exp.int_timestamp,
            iat=iat.int_timestamp,
            iss=settings.jwt_issuer if settings.jwt_issuer else None,
            jti=str(uuid.uuid4()),
            sub=sub,
            scope=scope,
        )

    def _generate_refresh_token(self, length: int = 16):
        return secrets.token_hex(length)

    def _generate_tokens(
        self,
        sub: str,
        scope: str | None = None,
    ) -> tuple[JWTToken, RefreshToken]:
        self._logger.info(f"Generating new tokens for sub={sub}")

        jwt_token = self._generate_token(sub, settings.jwt_token_lifetime, scope=scope)
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
        self, email: str, password: str, requested_scope: str | None = None
    ) -> tuple[str, str, int, str | None]:
        user = self._user_service_client.get_user_by_email(email)

        if user is None:
            raise InvalidCredentialsException(ERROR_MESSAGE_UNAUTHORIZED)

        try:
            self._password_hasher.verify(user["password"], password)
        except (InvalidHash, VerifyMismatchError):
            raise InvalidCredentialsException(ERROR_MESSAGE_UNAUTHORIZED)

        scope = self._derive_scope(user.get("roles", []), requested_scope)
        jwt_token, refresh_token = self._generate_tokens(user["id"], scope=scope)

        return (
            jwt.encode(jwt_token.model_dump(exclude_none=True), settings.jwt_secret),
            refresh_token.token,
            settings.jwt_token_lifetime,
            scope,
        )

    def logout(self, jwt_token: JWTToken):
        self._revoke_token(jwt_token)

    def refresh(self, refresh_token: str) -> tuple[str, str, int, str | None]:
        item = self._token_service.get_by_refresh_token(refresh_token)

        if item is None:
            self._logger.warning("The requested token was not found!")
            raise TokenNotFoundException(ERROR_MESSAGE_TOKEN_NOT_FOUND)

        if item["ttl"] < pendulum.now().int_timestamp:
            raise TokenExpiredException("The requested token has expired")

        self._token_service.delete_by_id(item["jwt_token"]["jti"])

        scope = item["jwt_token"].get("scope")
        sub = item["jwt_token"]["sub"]
        jwt_token, refresh_token = self._generate_tokens(sub, scope=scope)

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
                raise OAuthException(
                    "invalid_scope", status_code=status.HTTP_400_BAD_REQUEST
                )
            granted_scope = requested_scope
        else:
            granted_scope = " ".join(sorted(allowed)) if allowed else None

        jwt_token = self._generate_token(
            sub=client_id,
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

    def authorize(
        self,
        user_id: str,
        client_id: str,
        redirect_uri: str,
        requested_scope: str | None = None,
        code_challenge: str | None = None,
        code_challenge_method: str | None = None,
    ) -> str:
        user = self._user_service_client.get_user_by_id(user_id)
        if user is None:
            raise UserNotFoundException(ERROR_MESSAGE_USER_NOT_FOUND)

        scope = self._derive_scope(user.get("roles", []), requested_scope)

        code = self._authorization_code_repository.create(
            client_id=client_id,
            user_id=user_id,
            redirect_uri=redirect_uri,
            scope=scope,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
        )

        return code

    def exchange_code(
        self, code: str, redirect_uri: str, code_verifier: str | None = None
    ) -> tuple[str, str, int, str | None]:
        auth_code = self._authorization_code_repository.get_by_code(code)
        now = pendulum.now().int_timestamp

        if auth_code is None:
            raise OAuthException(
                "invalid_grant", status_code=status.HTTP_400_BAD_REQUEST
            )

        if auth_code.ttl < now:
            self._authorization_code_repository.delete_by_id(auth_code.id)
            raise OAuthException(
                "invalid_grant", status_code=status.HTTP_400_BAD_REQUEST
            )

        if auth_code.redirect_uri != redirect_uri:
            raise OAuthException(
                "invalid_grant", status_code=status.HTTP_400_BAD_REQUEST
            )

        self._validate_pkce(auth_code, code_verifier)

        self._authorization_code_repository.delete_by_id(auth_code.id)

        user = self._user_service_client.get_user_by_id(auth_code.user_id)
        if user is None:
            raise UserNotFoundException(ERROR_MESSAGE_USER_NOT_FOUND)

        jwt_token, refresh_token = self._generate_tokens(
            auth_code.user_id, scope=auth_code.scope
        )

        return (
            jwt.encode(jwt_token.model_dump(exclude_none=True), settings.jwt_secret),
            refresh_token.token,
            settings.jwt_token_lifetime,
            auth_code.scope,
        )
