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
logger = Logger()

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

        self._user_service_token = None

    def _derive_scope(
        self, roles: list[str], requested_scope: str | None
    ) -> str | None:
        self._logger.debug(
            "Deriving scope from roles",
            extra={"roles_count": len(roles), "requested_scope": requested_scope},
        )
        allowed_scopes: set[str] = set()
        for role in roles:
            allowed_scopes.update(ROLE_SCOPE_MAP.get(role, []))

        if not allowed_scopes:
            self._logger.info("No allowed scopes mapped for roles")
            return None

        if requested_scope:
            requested = set(requested_scope.split())
            if not requested.issubset(allowed_scopes):
                self._logger.warning(
                    "Requested scope contains unauthorized values",
                    extra={"requested_scope": requested_scope},
                )
                raise OAuthException("invalid_scope")
            return requested_scope

        return " ".join(sorted(allowed_scopes))

    @staticmethod
    def _get_pkce_challenge(
        code_verifier: str,
        code_challenge_method: str | None,
    ) -> str:
        if code_challenge_method == "S256":
            logger.debug("Computing PKCE challenge using S256")
            return (
                base64.urlsafe_b64encode(
                    hashlib.sha256(code_verifier.encode()).digest()
                )
                .decode()
                .rstrip("=")
            )

        if code_challenge_method == "plain":
            logger.debug("Computing PKCE challenge using plain method")
            return code_verifier

        logger.warning(
            "Unsupported PKCE code challenge method",
            extra={"code_challenge_method": code_challenge_method},
        )

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
            self._logger.debug("PKCE validation skipped, no code challenge present")
            return

        if not code_verifier:
            self._logger.warning("PKCE code_verifier is missing")
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
            self._logger.warning("PKCE challenge validation failed")
            raise OAuthException(
                "invalid_grant", status_code=status.HTTP_400_BAD_REQUEST
            )

    def _generate_token(
        self,
        sub: str,
        exp: int | None = None,
        scope: str | None = None,
    ) -> JWTToken:
        self._logger.debug(
            f"Generating JWT payload for sub={sub}",
            extra={"has_scope": scope is not None},
        )
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

    def _generate_refresh_token(self, length: int = 32):
        self._logger.debug(
            "Generating refresh token",
            extra={"token_length_bytes": length},
        )
        return secrets.token_hex(length)

    def _generate_tokens(
        self,
        sub: str,
        scope: str | None = None,
    ) -> tuple[JWTToken, RefreshToken]:
        self._logger.info(
            f"Generating new tokens for sub={sub}",
            extra={"has_scope": scope is not None},
        )

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

    def _issue_service_token(
        self, client_name: str, client_secret: str, scope: str | None = None
    ) -> JWTToken:
        if (
            self._user_service_token
            and self._user_service_token.exp > pendulum.now().int_timestamp
        ):
            self._logger.debug("Reusing cached user service token")
            return self._user_service_token

        self._logger.info("Issuing new user service token")

        service_token = self._generate_client_credentials(
            client_name, client_secret, scope
        )
        self._user_service_token = service_token

        return service_token

    def login(
        self, email: str, password: str, requested_scope: str | None = None
    ) -> tuple[str, str, int, str | None]:
        self._logger.info(
            "Login requested",
            extra={"requested_scope": requested_scope},
        )
        service_token = self._issue_service_token(
            settings.app_name, settings.client_secret
        )
        user = self._user_service_client.get_user_by_email(
            email,
            jwt.encode(
                service_token.model_dump(exclude_none=True), settings.jwt_secret
            ),
        )

        if user is None:
            self._logger.warning("Login failed, user not found")
            raise InvalidCredentialsException(ERROR_MESSAGE_UNAUTHORIZED)

        if not self._user_service_client.validate_user_password(
            user["id"],
            password,
            jwt.encode(
                service_token.model_dump(exclude_none=True), settings.jwt_secret
            ),
        ):
            self._logger.warning("Login failed, invalid credentials")
            raise InvalidCredentialsException(ERROR_MESSAGE_UNAUTHORIZED)

        scope = self._derive_scope(user.get("roles", []), requested_scope)
        service_token, refresh_token = self._generate_tokens(user["id"], scope=scope)
        self._logger.info(
            f"Login succeeded for sub={user['id']}",
            extra={"has_scope": scope is not None},
        )

        return (
            jwt.encode(
                service_token.model_dump(exclude_none=True), settings.jwt_secret
            ),
            refresh_token.token,
            settings.jwt_token_lifetime,
            scope,
        )

    def logout(self, jwt_token: JWTToken):
        self._logger.info(f"Logout requested for jti={jwt_token.jti}")
        self._revoke_token(jwt_token)

    def refresh(self, refresh_token: str) -> tuple[str, str, int, str | None]:
        self._logger.info("Refreshing access token")
        item = self._token_service.get_by_refresh_token(refresh_token)

        if item is None:
            self._logger.warning("The requested token was not found!")
            raise TokenNotFoundException(ERROR_MESSAGE_TOKEN_NOT_FOUND)

        if item["ttl"] < pendulum.now().int_timestamp:
            self._logger.warning(
                "Refresh token expired",
                extra={"jti": item["jwt_token"]["jti"]},
            )
            raise TokenExpiredException("The requested token has expired")

        if not self._token_service.consume_by_id(item["jwt_token"]["jti"]):
            self._logger.warning(
                "Token refresh failed, token already consumed",
                extra={"jti": item["jwt_token"]["jti"]},
            )
            raise TokenNotFoundException(ERROR_MESSAGE_TOKEN_NOT_FOUND)

        scope = item["jwt_token"].get("scope")
        sub = item["jwt_token"]["sub"]
        jwt_token, refresh_token = self._generate_tokens(sub, scope=scope)
        self._logger.info(
            f"Token refresh succeeded for sub={sub}",
            extra={"has_scope": scope is not None},
        )

        return (
            jwt.encode(jwt_token.model_dump(exclude_none=True), settings.jwt_secret),
            refresh_token.token,
            settings.jwt_token_lifetime,
            scope,
        )

    def _generate_client_credentials(
        self, client_name: str, client_secret: str, requested_scope: str | None
    ) -> JWTToken:
        self._logger.info(
            f"Generating client credentials token for client_name={client_name}",
            extra={"requested_scope": requested_scope},
        )
        service = self._service_repository.get_by_name(client_name)
        if service is None:
            self._logger.warning(
                f"Client credentials failed, service not found for client_name={client_name}"
            )
            raise OAuthException(
                "invalid_client",
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": "Basic"},
            )
        try:
            self._password_hasher.verify(service.secret, client_secret)
        except (InvalidHash, VerifyMismatchError):
            self._logger.warning(
                f"Client credentials failed, invalid secret for client_name={client_name}"
            )
            raise OAuthException(
                "invalid_client",
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": "Basic"},
            )

        allowed = set(service.scopes)
        if requested_scope:
            requested = set(requested_scope.split())
            if not requested.issubset(allowed):
                self._logger.warning(
                    "Client credentials requested invalid scope",
                    extra={
                        "client_name": client_name,
                        "requested_scope": requested_scope,
                    },
                )
                raise OAuthException(
                    "invalid_scope", status_code=status.HTTP_400_BAD_REQUEST
                )
            granted_scope = requested_scope
        else:
            granted_scope = " ".join(sorted(allowed)) if allowed else None

        jwt_token = self._generate_token(
            sub=client_name,
            exp=settings.service_token_lifetime,
            scope=granted_scope,
        )
        self._token_service.create(
            jwt_token,
            None,
        )

        self._logger.info(
            f"Client credentials token created for client_name={client_name}",
            extra={"has_scope": granted_scope is not None},
        )

        return jwt_token

    def client_credentials(
        self, client_name: str, client_secret: str, scope: str | None = None
    ) -> tuple[str, int, str | None]:
        self._logger.info(
            f"Client credentials flow requested for client_name={client_name}",
            extra={"requested_scope": scope},
        )
        jwt_token = self._generate_client_credentials(client_name, client_secret, scope)
        return (
            jwt.encode(jwt_token.model_dump(exclude_none=True), settings.jwt_secret),
            settings.service_token_lifetime,
            jwt_token.scope,
        )

    def authorize(
        self,
        user_id: str,
        client_id: str,
        redirect_uri: str,
        requested_scope: str | None = None,
        code_challenge: str | None = None,
        code_challenge_method: str | None = None,
    ) -> str:
        self._logger.info(
            f"Authorization code requested for user_id={user_id}",
            extra={"client_id": client_id, "requested_scope": requested_scope},
        )
        service_token = self._issue_service_token(
            settings.app_name, settings.client_secret
        )
        user = self._user_service_client.get_user_by_id(
            user_id,
            jwt.encode(
                service_token.model_dump(exclude_none=True), settings.jwt_secret
            ),
        )
        if user is None:
            self._logger.warning(
                f"Authorization failed, user not found user_id={user_id}"
            )
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

        self._logger.info(
            f"Authorization code created for user_id={user_id}",
            extra={"client_id": client_id, "has_scope": scope is not None},
        )

        return code

    def exchange_code(
        self, code: str, redirect_uri: str, code_verifier: str | None = None
    ) -> tuple[str, str, int, str | None]:
        self._logger.info("Authorization code exchange requested")
        auth_code = self._authorization_code_repository.get_by_code(code)
        now = pendulum.now().int_timestamp

        if auth_code is None:
            self._logger.warning("Authorization code exchange failed, code not found")
            raise OAuthException(
                "invalid_grant", status_code=status.HTTP_400_BAD_REQUEST
            )

        if not self._authorization_code_repository.consume_by_id(auth_code.id):
            self._logger.warning(
                "Authorization code exchange failed, code already consumed",
                extra={"authorization_code_id": auth_code.id},
            )
            raise OAuthException(
                "invalid_grant", status_code=status.HTTP_400_BAD_REQUEST
            )

        if auth_code.ttl < now:
            self._logger.warning(
                "Authorization code exchange failed, code expired",
                extra={"authorization_code_id": auth_code.id},
            )
            raise OAuthException(
                "invalid_grant", status_code=status.HTTP_400_BAD_REQUEST
            )

        if auth_code.redirect_uri != redirect_uri:
            self._logger.warning(
                "Authorization code exchange failed, redirect_uri mismatch",
                extra={"authorization_code_id": auth_code.id},
            )
            raise OAuthException(
                "invalid_grant", status_code=status.HTTP_400_BAD_REQUEST
            )

        self._validate_pkce(auth_code, code_verifier)

        jwt_token = self._issue_service_token(settings.app_name, settings.client_secret)
        user = self._user_service_client.get_user_by_id(
            auth_code.user_id,
            jwt.encode(jwt_token.model_dump(exclude_none=True), settings.jwt_secret),
        )
        if user is None:
            self._logger.warning(
                f"Authorization code exchange failed, user not found user_id={auth_code.user_id}"
            )
            raise UserNotFoundException(ERROR_MESSAGE_USER_NOT_FOUND)

        jwt_token, refresh_token = self._generate_tokens(
            auth_code.user_id, scope=auth_code.scope
        )

        self._logger.info(
            f"Authorization code exchange succeeded for user_id={auth_code.user_id}",
            extra={"has_scope": auth_code.scope is not None},
        )

        return (
            jwt.encode(jwt_token.model_dump(exclude_none=True), settings.jwt_secret),
            refresh_token.token,
            settings.jwt_token_lifetime,
            auth_code.scope,
        )
