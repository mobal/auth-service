import base64
import hashlib
import secrets
import time
import uuid
from urllib.parse import urlparse, urlunparse

import jwt
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
from app.models.service import ServiceCredential
from app.repositories.authorization_code_repository import AuthorizationCodeRepository
from app.repositories.service_repository import ServiceRepository
from app.services.token_service import TokenService

ERROR_MESSAGE_UNAUTHORIZED = "Unauthorized"
ERROR_MESSAGE_TOKEN_NOT_FOUND = "The requested token was not found"
ERROR_MESSAGE_USER_NOT_FOUND = "The requested user was not found"

ROLE_SCOPE_MAP: dict[str, list[str]] = {
    "root": ["tokens:revoke", "users:read", "users:write"],
}


def _invalid_client_error() -> OAuthException:
    """Build the ``invalid_client`` error response (RFC 6749 Section 5.2)."""
    return OAuthException(
        "invalid_client",
        status_code=status.HTTP_401_UNAUTHORIZED,
        headers={"WWW-Authenticate": "Basic"},
    )


class AuthService:
    """OAuth 2.0 flow orchestration over repositories and outbound clients."""

    def __init__(
        self,
        password_hasher: PasswordHasher,
        authorization_code_repository: AuthorizationCodeRepository,
        service_repository: ServiceRepository,
        token_service: TokenService,
        user_service_client: UserServiceClient,
    ) -> None:
        self._logger = Logger()
        self._password_hasher = password_hasher
        self._authorization_code_repository = authorization_code_repository
        self._service_repository = service_repository
        self._token_service = token_service
        self._user_service_client = user_service_client

        self._user_service_token = None

    def _derive_scope(
        self, roles: list[str], requested_scope: str | None
    ) -> str | None:
        self._logger.debug(
            "Deriving scope from roles",
            extra={"roles_count": len(roles), "requested_scope": requested_scope},
        )
        allowed_scopes = {
            scope for role in roles for scope in ROLE_SCOPE_MAP.get(role, [])
        }
        if not allowed_scopes:
            self._logger.info("No allowed scopes mapped for roles")
            return None
        return self._resolve_scope(allowed_scopes, requested_scope)

    def _resolve_scope(
        self,
        allowed_scopes: set[str],
        requested_scope: str | None,
        log_context: dict | None = None,
    ) -> str | None:
        """Negotiate the granted scope against the allowed set.

        Returns the requested scope verbatim when it is fully allowed,
        otherwise the full allowed set (``None`` when it is empty).  Raises
        ``invalid_scope`` when the request contains unauthorized values.
        """
        if requested_scope:
            requested = set(requested_scope.split())
            if not requested.issubset(allowed_scopes):
                self._logger.warning(
                    "Requested scope contains unauthorized values",
                    extra={"requested_scope": requested_scope, **(log_context or {})},
                )
                raise OAuthException("invalid_scope")
            return requested_scope
        return " ".join(sorted(allowed_scopes)) if allowed_scopes else None

    def _get_pkce_challenge(
        self,
        code_verifier: str,
        code_challenge_method: str | None,
    ) -> str:
        method = code_challenge_method or "plain"

        if method == "S256":
            self._logger.debug("Computing PKCE challenge using S256")
            return (
                base64.urlsafe_b64encode(
                    hashlib.sha256(code_verifier.encode()).digest()
                )
                .decode()
                .rstrip("=")
            )

        if method == "plain":
            self._logger.debug("Computing PKCE challenge using plain method")
            return code_verifier

        self._logger.warning(
            "Unsupported PKCE code challenge method",
            extra={"code_challenge_method": method},
        )
        raise OAuthException(
            "invalid_request",
            "Unsupported code_challenge_method",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    @staticmethod
    def _normalize_uri(uri: str) -> str:
        parsed = urlparse(uri)
        scheme = parsed.scheme.lower()
        host = parsed.hostname.lower() if parsed.hostname else ""
        port = parsed.port
        default_port = {"https": 443, "http": 80}.get(scheme)
        if port == default_port:
            port = None
        path = parsed.path.rstrip("/") or "/"
        netloc = f"{host}:{port}" if port else host
        return urlunparse(
            (scheme, netloc, path, parsed.params, parsed.query, parsed.fragment)
        )

    def _validate_pkce(
        self,
        auth_code: AuthorizationCode,
        code_verifier: str | None,
    ) -> None:
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
        if not secrets.compare_digest(expected_challenge, auth_code.code_challenge):
            self._logger.warning("PKCE challenge validation failed")
            raise OAuthException(
                "invalid_grant", status_code=status.HTTP_400_BAD_REQUEST
            )

    def _generate_token(
        self,
        sub: str,
        lifetime: int,
        scope: str | None = None,
        aud: str | None = None,
    ) -> JWTToken:
        """Build a JWT access-token payload valid for ``lifetime`` seconds."""
        self._logger.debug(
            "Generating JWT payload for sub=%s",
            sub,
            extra={"sub": sub, "has_scope": scope is not None},
        )
        iat = int(time.time())
        issuer = f"{settings.stage}-{settings.app_name}"

        return JWTToken(
            exp=iat + lifetime,
            iat=iat,
            iss=issuer,
            # Default the audience to this service's own identity: tokens are
            # re-presented to its bearer-protected endpoints (/oauth/authorize,
            # /oauth/revoke), which require ``aud`` to match the issuer.
            # Callers targeting another service (e.g. the user-service checks)
            # pass an explicit audience instead.
            aud=aud or issuer,
            jti=str(uuid.uuid4()),
            sub=sub,
            scope=scope,
        )

    def _generate_refresh_token(self, length: int = 32) -> str:
        self._logger.debug(
            "Generating refresh token",
            extra={"token_length_bytes": length},
        )
        return secrets.token_hex(length)

    def _generate_tokens(
        self,
        sub: str,
        scope: str | None = None,
        aud: str | None = None,
    ) -> tuple[JWTToken, RefreshToken]:
        """Issue and persist a new access/refresh token pair for ``sub``."""
        self._logger.info(
            "Generating new tokens for sub=%s",
            sub,
            extra={"sub": sub, "has_scope": scope is not None},
        )
        jwt_token = self._generate_token(
            sub, settings.jwt_token_lifetime, scope=scope, aud=aud
        )
        refresh_token = RefreshToken(
            token=self._generate_refresh_token(),
            ttl=jwt_token.iat + settings.refresh_token_lifetime,
        )
        self._token_service.create(jwt_token, refresh_token)
        return jwt_token, refresh_token

    @staticmethod
    def _encode_token(token: JWTToken) -> str:
        """Sign a JWT payload with the auth-service signing secret."""
        return jwt.encode(token.model_dump(exclude_none=True), settings.jwt_secret)

    def _token_response(
        self, jwt_token: JWTToken, refresh_token: RefreshToken
    ) -> tuple[str, str, int, str | None]:
        """Build the token-endpoint response for a fresh token pair."""
        return (
            self._encode_token(jwt_token),
            refresh_token.token,
            settings.jwt_token_lifetime,
            jwt_token.scope,
        )

    def _revoke_token(self, jwt_token: JWTToken) -> None:
        self._logger.info(
            "Revoking token with jti=%s",
            jwt_token.jti,
            extra={"token_sub": jwt_token.sub, "token_scope": jwt_token.scope},
        )
        self._token_service.delete_by_id(jwt_token.jti)

    def _service_token_is_fresh(self, token: JWTToken) -> bool:
        """Return whether a cached service token still has enough lifetime.

        Cache with a safety buffer: refresh when less than 20% of the lifetime
        remains or at most 60s before expiry, to reduce the window for serving
        revoked tokens.
        """
        remaining = token.exp - int(time.time())
        safety_buffer = max(settings.service_token_lifetime_seconds // 5, 60)
        return remaining > safety_buffer

    def _issue_service_token(
        self,
        client_name: str,
        client_secret: str,
        scope: str | None = None,
        aud: str | None = None,
    ) -> JWTToken:
        """Issue (or reuse) the service-to-service token for this client."""
        if self._user_service_token is not None and self._service_token_is_fresh(
            self._user_service_token
        ):
            self._logger.debug("Reusing cached user service token")
            return self._user_service_token

        self._logger.info("Issuing new user service token")
        self._user_service_token = self._generate_client_credentials(
            client_name, client_secret, scope, aud
        )
        return self._user_service_token

    def _authenticate_service(
        self, client_name: str, client_secret: str
    ) -> ServiceCredential:
        """Resolve and authenticate a registered service credential."""
        service = self._service_repository.get_by_name(client_name)
        if service is None:
            self._logger.warning(
                "Client credentials failed, service not found for client_name=%s",
                client_name,
                extra={"client_name": client_name},
            )
            raise _invalid_client_error()

        try:
            self._password_hasher.verify(service.secret, client_secret)
        except (InvalidHash, VerifyMismatchError):
            self._logger.warning(
                "Client credentials failed, invalid secret for client_name=%s",
                client_name,
                extra={"client_name": client_name},
            )
            raise _invalid_client_error()

        return service

    def _generate_client_credentials(
        self,
        client_name: str,
        client_secret: str,
        requested_scope: str | None,
        aud: str | None = None,
    ) -> JWTToken:
        """Authenticate a client and issue its access token (RFC 6749 4.4)."""
        self._logger.info(
            "Generating client credentials token for client_name=%s",
            client_name,
            extra={"client_name": client_name, "requested_scope": requested_scope},
        )
        service = self._authenticate_service(client_name, client_secret)
        granted_scope = self._resolve_scope(
            set(service.scopes or []),
            requested_scope,
            log_context={"client_name": client_name},
        )
        jwt_token = self._generate_token(
            sub=client_name,
            lifetime=settings.service_token_lifetime_seconds,
            scope=granted_scope,
            aud=aud,
        )
        self._token_service.create(jwt_token, None)

        self._logger.info(
            "Client credentials token created for client_name=%s",
            client_name,
            extra={"client_name": client_name, "has_scope": granted_scope is not None},
        )
        return jwt_token

    def _fetch_user_by_email(self, email: str) -> dict | None:
        """Fetch a user from the user service by email."""
        service_token = self._issue_service_token(
            settings.app_name,
            settings.client_secret,
            aud=f"{settings.stage}-user-service",
        )
        return self._user_service_client.get_user_by_email(
            email, self._encode_token(service_token)
        )

    def _fetch_user_by_id(self, user_id: str, failure_context: str) -> dict:
        """Fetch a user by id, raising ``UserNotFoundException`` if missing."""
        service_token = self._issue_service_token(
            settings.app_name,
            settings.client_secret,
            aud=f"{settings.stage}-user-service",
        )
        user = self._user_service_client.get_user_by_id(
            user_id, self._encode_token(service_token)
        )
        if user is None:
            self._logger.warning(
                "%s failed, user not found user_id=%s",
                failure_context,
                user_id,
                extra={"user_id": user_id},
            )
            raise UserNotFoundException(ERROR_MESSAGE_USER_NOT_FOUND)
        return user

    def _validate_user_password(self, user_id: str, password: str) -> bool:
        """Ask the user service to verify a password for ``user_id``."""
        service_token = self._issue_service_token(
            settings.app_name,
            settings.client_secret,
            aud=f"{settings.stage}-user-service",
        )
        return self._user_service_client.validate_user_password(
            user_id, password, self._encode_token(service_token)
        )

    def _validate_redirect_uri(self, client_id: str, redirect_uri: str) -> None:
        try:
            client = self._service_repository.get_by_id(client_id)
        except Exception:
            # Skip validation when the client cannot be resolved rather than
            # breaking the authorization flow.
            return
        if not client or not client.redirect_uris:
            return

        normalized_redirect = self._normalize_uri(redirect_uri)
        if not any(
            self._normalize_uri(allowed) == normalized_redirect
            for allowed in client.redirect_uris
        ):
            self._logger.warning(
                "Authorization failed, redirect_uri not registered for client_id=%s",
                client_id,
            )
            raise OAuthException(
                "invalid_request",
                "Redirect URI is not registered for this client",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

    def login(
        self, email: str, password: str, requested_scope: str | None = None
    ) -> tuple[str, str, int, str | None]:
        # ⚠️  SECURITY NOTICE — Password Grant (RFC 6749 Section 4.3)
        #
        # This flow exposes the resource owner's credentials to the client,
        # which violates OAuth 2.1 best practices.  It SHOULD only be used
        # when the client is the resource owner (e.g. a first-party app)
        # and no other grant type is feasible.
        #
        # Deprecation plan:  Remove this flow once all clients have migrated
        # to the authorization code grant with PKCE.
        self._logger.warning(
            "Password grant login invoked — this flow is deprecated per OAuth 2.1 (BCP). "
            "Migrate to authorization code grant with PKCE.",
            extra={"email": email, "requested_scope": requested_scope},
        )
        user = self._fetch_user_by_email(email)
        if user is None:
            self._logger.warning("Login failed, user not found")
            raise InvalidCredentialsException(ERROR_MESSAGE_UNAUTHORIZED)

        if not self._validate_user_password(user["id"], password):
            self._logger.warning("Login failed, invalid credentials")
            raise InvalidCredentialsException(ERROR_MESSAGE_UNAUTHORIZED)

        scope = self._derive_scope(user.get("roles", []), requested_scope)
        access_token, refresh_token = self._generate_tokens(user["id"], scope=scope)
        self._logger.info(
            "Login succeeded for sub=%s",
            user["id"],
            extra={"sub": user["id"], "has_scope": scope is not None},
        )
        return self._token_response(access_token, refresh_token)

    def logout(self, jwt_token: JWTToken) -> None:
        self._logger.info("Logout requested for jti=%s", jwt_token.jti)
        self._revoke_token(jwt_token)

    def refresh(self, refresh_token: str) -> tuple[str, str, int, str | None]:
        """Rotate a refresh token into a new access/refresh token pair."""
        self._logger.info("Refreshing access token")
        item = self._token_service.get_by_refresh_token(refresh_token)
        if item is None:
            self._logger.warning("The requested token was not found!")
            raise TokenNotFoundException(ERROR_MESSAGE_TOKEN_NOT_FOUND)

        jwt_token, _, ttl = item
        if ttl < int(time.time()):
            self._logger.warning("Refresh token expired", extra={"jti": jwt_token.jti})
            raise TokenExpiredException("The requested token has expired")

        if not self._token_service.consume_by_id(jwt_token.jti):
            self._logger.warning(
                "Token refresh failed, token already consumed",
                extra={"jti": jwt_token.jti},
            )
            raise TokenNotFoundException(ERROR_MESSAGE_TOKEN_NOT_FOUND)

        access_token, new_refresh_token = self._generate_tokens(
            jwt_token.sub, scope=jwt_token.scope
        )
        self._logger.info(
            "Token refresh succeeded for sub=%s",
            jwt_token.sub,
            extra={"sub": jwt_token.sub, "has_scope": jwt_token.scope is not None},
        )
        return self._token_response(access_token, new_refresh_token)

    def client_credentials(
        self,
        client_name: str,
        client_secret: str,
        scope: str | None = None,
        aud: str | None = None,
    ) -> tuple[str, int, str | None]:
        """Issue a client-credentials access token (RFC 6749 Section 4.4)."""
        self._logger.info(
            "Client credentials flow requested for client_name=%s",
            client_name,
            extra={"client_name": client_name, "requested_scope": scope},
        )
        jwt_token = self._generate_client_credentials(
            client_name, client_secret, scope, aud
        )
        return (
            self._encode_token(jwt_token),
            settings.service_token_lifetime_seconds,
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
        """Create an authorization code for the user and client (RFC 6749 4.1)."""
        self._logger.info(
            "Authorization code requested for user_id=%s",
            user_id,
            extra={
                "user_id": user_id,
                "client_id": client_id,
                "requested_scope": requested_scope,
            },
        )
        user = self._fetch_user_by_id(user_id, "Authorization")
        self._validate_redirect_uri(client_id, redirect_uri)

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
            "Authorization code created for user_id=%s",
            user_id,
            extra={
                "user_id": user_id,
                "client_id": client_id,
                "has_scope": scope is not None,
            },
        )
        return code

    def _load_auth_code(
        self, code: str, redirect_uri: str, code_verifier: str | None
    ) -> AuthorizationCode:
        """Fetch and validate an authorization code for exchange.

        Consumes the code unconditionally once found, then verifies expiry,
        redirect URI, and PKCE — raising ``invalid_grant`` on any mismatch.
        """
        auth_code = self._authorization_code_repository.get_by_code(code)
        if auth_code is None:
            self._logger.warning("Authorization code exchange failed, code not found")
            raise OAuthException("invalid_grant")

        if not self._authorization_code_repository.consume_by_id(auth_code.id):
            self._logger.warning(
                "Authorization code exchange failed, code already consumed",
                extra={"authorization_code_id": auth_code.id},
            )
            raise OAuthException("invalid_grant")

        if auth_code.ttl < int(time.time()):
            self._logger.warning(
                "Authorization code exchange failed, code expired",
                extra={"authorization_code_id": auth_code.id},
            )
            raise OAuthException("invalid_grant")

        if self._normalize_uri(auth_code.redirect_uri) != self._normalize_uri(
            redirect_uri
        ):
            self._logger.warning(
                "Authorization code exchange failed, redirect_uri mismatch",
                extra={"authorization_code_id": auth_code.id},
            )
            raise OAuthException("invalid_grant")

        self._validate_pkce(auth_code, code_verifier)
        return auth_code

    def exchange_code(
        self, code: str, redirect_uri: str, code_verifier: str | None = None
    ) -> tuple[str, str, int, str | None]:
        """Exchange a valid authorization code for tokens (RFC 6749 4.1.3)."""
        self._logger.info("Authorization code exchange requested")
        auth_code = self._load_auth_code(code, redirect_uri, code_verifier)

        self._fetch_user_by_id(auth_code.user_id, "Authorization code exchange")

        access_token, refresh_token = self._generate_tokens(
            auth_code.user_id, scope=auth_code.scope
        )
        self._logger.info(
            "Authorization code exchange succeeded for user_id=%s",
            auth_code.user_id,
            extra={
                "user_id": auth_code.user_id,
                "has_scope": auth_code.scope is not None,
            },
        )
        return self._token_response(access_token, refresh_token)
