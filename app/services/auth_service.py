import base64
import hashlib
import re
import secrets
import time
import uuid
from typing import cast
from urllib.parse import urlparse, urlunparse

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerifyMismatchError
from aws_lambda_powertools import Logger
from starlette import status

from app import settings
from app.clients.google_oidc_client import GoogleOIDCClient
from app.clients.user_service_client import UserServiceClient
from app.exceptions import (
    GoogleOIDCValidationError,
    InvalidCredentialsException,
    OAuthException,
    TokenExpiredException,
    TokenNotFoundException,
    UserNotFoundException,
)
from app.models.authorization_code import AuthorizationCode
from app.models.authorization_decision import AuthorizationDecision
from app.models.google_identity import GoogleIdentity
from app.models.google_login_result import GoogleLoginResult
from app.models.jwt import JWTToken, RefreshToken
from app.models.pending_authorization_request import PendingAuthorizationRequest
from app.models.request.oauth_token import (
    AuthorizationCodeGrantRequest,
    BaseGrantRequest,
    ClientCredentialsGrantRequest,
    PasswordGrantRequest,
    RefreshTokenGrantRequest,
)
from app.models.response.token import OAuthTokenResponse
from app.models.service import ServiceCredential
from app.repositories.audience_repository import AudienceRepository
from app.repositories.authorization_code_repository import AuthorizationCodeRepository
from app.repositories.browser_session_repository import BrowserSessionRepository
from app.repositories.google_oidc_state_repository import GoogleOIDCStateRepository
from app.repositories.pending_authorization_request_repository import (
    PendingAuthorizationRequestRepository,
)
from app.repositories.role_scope_repository import RoleScopeRepository
from app.repositories.service_repository import ServiceRepository
from app.services.token_service import TokenService

ERROR_MESSAGE_UNAUTHORIZED = "Unauthorized"
ERROR_MESSAGE_TOKEN_NOT_FOUND = "The requested token was not found"
ERROR_MESSAGE_USER_NOT_FOUND = "The requested user was not found"
ERROR_MESSAGE_UNSUPPORTED_RESPONSE_TYPE = "Unsupported response type"


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
        role_scope_repository: RoleScopeRepository,
        audience_repository: AudienceRepository | None = None,
    ) -> None:
        self._logger = Logger()
        self._password_hasher = password_hasher
        self._authorization_code_repository = authorization_code_repository
        self._service_repository = service_repository
        self._token_service = token_service
        self._user_service_client = user_service_client
        self._role_scope_repository = role_scope_repository
        self._audience_repository = audience_repository

        self._user_service_token = None

    def _audience_is_registered(self, audience: str) -> bool:
        """Return whether the audience exists in the registry."""
        if self._audience_repository is None:
            self._logger.warning(
                "Audience requested but no audience registry is configured",
                extra={"audience": audience},
            )
            return False
        return self._audience_repository.get_by_audience(audience) is not None

    def _validate_audience(self, audience: str, client_name: str) -> None:
        """Check the audience registry before issuing a targeted token.

        The registry defines which audiences exist and which clients may
        request tokens for them.  Raises ``invalid_target`` for unregistered
        audiences and ``unauthorized_client`` when the client is not allowed.
        """
        if self._audience_repository is None:
            self._logger.warning(
                "Audience requested but no audience registry is configured",
                extra={"audience": audience},
            )
            raise OAuthException(
                "invalid_target",
                "Audience registry is not available",
            )

        audience_item = self._audience_repository.get_by_audience(audience)
        if audience_item is None:
            self._logger.warning(
                "Audience validation failed, audience not registered",
                extra={"audience": audience, "client_name": client_name},
            )
            raise OAuthException(
                "invalid_target",
                "The requested audience is not registered",
            )

        if client_name not in audience_item.allowed_clients:
            self._logger.warning(
                "Audience validation failed, client not allowed for audience",
                extra={"audience": audience, "client_name": client_name},
            )
            raise OAuthException(
                "unauthorized_client",
                "The client is not allowed to request tokens for this audience",
            )

    def _derive_scope(
        self, roles: list[str], requested_scope: str | None
    ) -> str | None:
        self._logger.debug(
            "Deriving scope from roles",
            extra={"roles_count": len(roles), "requested_scope": requested_scope},
        )
        role_scope_map = self._role_scope_repository.get_by_roles(roles)
        allowed_scopes = {
            scope for role in roles for scope in role_scope_map.get(role, [])
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

        if auth_code.code_challenge_method == "S256" and not re.fullmatch(
            r"[A-Za-z0-9\-._~]{43,128}", code_verifier
        ):
            self._logger.warning("PKCE code_verifier format validation failed")
            raise OAuthException(
                "invalid_grant", status_code=status.HTTP_400_BAD_REQUEST
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
        return jwt.encode(
            token.model_dump(exclude_none=True), cast(str, settings.jwt_secret)
        )

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
        if (
            service.allowed_grant_types is not None
            and "client_credentials" not in service.allowed_grant_types
        ):
            raise OAuthException("unauthorized_client")
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
            cast(str, settings.client_secret),
            aud=f"{settings.stage}-user-service",
        )
        return self._user_service_client.get_user_by_email(
            email, self._encode_token(service_token)
        )

    def _fetch_user_by_id(self, user_id: str, failure_context: str) -> dict:
        """Fetch a user by id, raising ``UserNotFoundException`` if missing."""
        service_token = self._issue_service_token(
            settings.app_name,
            cast(str, settings.client_secret),
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
            cast(str, settings.client_secret),
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

        if redirect_uri not in client.redirect_uris:
            self._logger.warning(
                "Authorization failed, redirect_uri not registered for client_id=%s",
                client_id,
            )
            raise OAuthException(
                "invalid_request",
                "Redirect URI is not registered for this client",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

    def validate_authorization_request(
        self,
        response_type: str,
        client_id: str,
        redirect_uri: str,
        code_challenge: str | None,
        code_challenge_method: str | None,
    ) -> tuple[str, str]:
        """Validate the browser-facing authorization request before login."""
        if response_type != "code":
            raise OAuthException("unsupported_response_type")
        if not code_challenge or code_challenge_method != "S256":
            raise OAuthException(
                "invalid_request",
                "SPA clients must use PKCE with S256",
            )

        client = self._service_repository.get_by_id(client_id)
        if client is None:
            raise OAuthException("invalid_client", "Unknown client")
        if (
            client.allowed_grant_types is not None
            and "authorization_code" not in client.allowed_grant_types
        ):
            raise OAuthException("unauthorized_client")
        if not client.redirect_uris:
            raise OAuthException(
                "invalid_request", "Client has no registered redirect URI"
            )
        if urlparse(redirect_uri).fragment:
            raise OAuthException(
                "invalid_request", "Redirect URI must not contain a fragment"
            )

        normalized_redirect = self._normalize_uri(redirect_uri)
        if not any(
            self._normalize_uri(allowed) == normalized_redirect
            for allowed in client.redirect_uris
        ):
            raise OAuthException(
                "invalid_request",
                "Redirect URI is not registered for this client",
            )
        if code_challenge is None or code_challenge_method is None:
            raise OAuthException(
                "invalid_request",
                "PKCE parameters are required for browser authorization",
            )
        return code_challenge, code_challenge_method

    def process_authorization_request(
        self,
        *,
        response_type: str,
        client_id: str,
        redirect_uri: str,
        scope: str | None,
        state: str | None,
        code_challenge: str | None,
        code_challenge_method: str | None,
        bearer_user_id: str | None,
        browser_session_user_id: str | None,
        pending_requests: PendingAuthorizationRequestRepository,
    ) -> AuthorizationDecision:
        """Validate and process an OAuth authorization request.

        A bearer-authenticated request is completed immediately. A browser
        request is validated for PKCE and either completed from an existing
        browser session or persisted for the login flow.
        """
        if bearer_user_id is not None:
            if response_type != "code":
                raise OAuthException(ERROR_MESSAGE_UNSUPPORTED_RESPONSE_TYPE)
            code = self.authorize(
                user_id=bearer_user_id,
                client_id=client_id,
                redirect_uri=redirect_uri,
                requested_scope=scope,
                code_challenge=code_challenge,
                code_challenge_method=code_challenge_method,
            )
            return AuthorizationDecision(
                redirect_uri=redirect_uri,
                state=state,
                authorization_code=code,
            )

        validated_challenge, validated_method = self.validate_authorization_request(
            response_type,
            client_id,
            redirect_uri,
            code_challenge,
            code_challenge_method,
        )
        if browser_session_user_id is not None:
            code = self.authorize(
                user_id=browser_session_user_id,
                client_id=client_id,
                redirect_uri=redirect_uri,
                requested_scope=scope,
                code_challenge=validated_challenge,
                code_challenge_method=validated_method,
            )
            return AuthorizationDecision(
                redirect_uri=redirect_uri,
                state=state,
                authorization_code=code,
            )

        request_id = pending_requests.create(
            client_id=client_id,
            redirect_uri=redirect_uri,
            response_type=response_type,
            scope=scope,
            state=state,
            code_challenge=validated_challenge,
            code_challenge_method=validated_method,
            lifetime_seconds=settings.pending_authorization_request_lifetime_seconds,
        )
        pending = pending_requests.get(request_id)
        if pending is None:
            raise OAuthException("invalid_request")
        return AuthorizationDecision(
            redirect_uri=redirect_uri,
            pending_request=pending,
        )

    def authorize_pending_request(
        self,
        pending: PendingAuthorizationRequest,
        user_id: str,
    ) -> str:
        """Issue an authorization code for a completed browser login."""
        return self.authorize(
            user_id=user_id,
            client_id=pending.client_id,
            redirect_uri=pending.redirect_uri,
            requested_scope=pending.scope,
            code_challenge=pending.code_challenge,
            code_challenge_method=pending.code_challenge_method,
        )

    def get_pending_authorization_request(
        self,
        request_id: str,
        pending_requests: PendingAuthorizationRequestRepository,
    ) -> PendingAuthorizationRequest | None:
        return pending_requests.get(request_id)

    def authenticate_user(self, email: str, password: str) -> dict:
        """Authenticate a browser user without issuing OAuth tokens."""
        user = self._fetch_user_by_email(email)
        if user is None or not self._validate_user_password(user["id"], password):
            raise InvalidCredentialsException("Invalid email or password.")
        return user

    def authenticate_google_user(self, identity: GoogleIdentity) -> dict:
        """Resolve a verified Google email to an existing local user.

        This is a temporary development path until user-service owns external
        identity records. It is deliberately disabled by default.
        """
        if not settings.google_dev_email_login_enabled:
            raise OAuthException("access_denied", "Google login is not enabled")
        user = self._fetch_user_by_email(str(identity.email))
        if user is None:
            raise OAuthException(
                "access_denied", "No local account matches Google email"
            )
        return user

    def start_google_login(
        self,
        request_id: str,
        csrf_token: str | None,
        pending_requests: PendingAuthorizationRequestRepository,
        google_states: GoogleOIDCStateRepository,
        google_client: GoogleOIDCClient,
    ) -> str | None:
        """Validate a pending browser login and return Google's auth URL."""
        pending = pending_requests.get(request_id)
        if pending is None or csrf_token != pending.csrf_token:
            return None
        oidc_state = google_states.create(
            pending_request_id=request_id,
            lifetime_seconds=settings.pending_authorization_request_lifetime_seconds,
        )
        return google_client.authorization_url(oidc_state.state, oidc_state.nonce)

    def complete_google_login(
        self,
        code: str | None,
        state: str | None,
        error: str | None,
        pending_requests: PendingAuthorizationRequestRepository,
        google_states: GoogleOIDCStateRepository,
        google_client: GoogleOIDCClient,
    ) -> GoogleLoginResult:
        """Validate Google's callback and resolve its local user."""
        if not state:
            return GoogleLoginResult(
                status="invalid_request", error_message="Invalid Google login state."
            )
        oidc_state = google_states.consume(state)
        if oidc_state is None:
            return GoogleLoginResult(
                status="invalid_request", error_message="Invalid Google login state."
            )
        pending = pending_requests.get(oidc_state.pending_request_id)
        if pending is None:
            return GoogleLoginResult(status="invalid_request")
        if error:
            return GoogleLoginResult(
                status="error", pending=pending, error_message=error
            )
        if not code:
            return GoogleLoginResult(
                status="error",
                pending=pending,
                error_message="Google did not return an authorization code.",
            )
        try:
            token_response = google_client.exchange_code(code)
            id_token = token_response.get("id_token")
            if not isinstance(id_token, str):
                raise GoogleOIDCValidationError("Google did not return an ID token")
            identity = google_client.validate_id_token(id_token, oidc_state.nonce)
            user = self.authenticate_google_user(identity)
        except GoogleOIDCValidationError:
            return GoogleLoginResult(
                status="error",
                pending=pending,
                error_message="Google authentication could not be verified.",
            )
        except OAuthException as oauth_error:
            return GoogleLoginResult(
                status="error",
                pending=pending,
                error_message=str(
                    oauth_error.detail.get("error_description", "Google login failed")
                ),
            )

        consumed = pending_requests.consume(oidc_state.pending_request_id)
        if consumed is None:
            return GoogleLoginResult(status="invalid_request")
        return GoogleLoginResult(status="success", pending=consumed, user_id=user["id"])

    def complete_browser_login(
        self,
        request_id: str,
        csrf_token: str | None,
        login_csrf: str | None,
        email: str,
        password: str,
        pending_requests: PendingAuthorizationRequestRepository,
    ) -> tuple[PendingAuthorizationRequest, dict] | None:
        """Validate, authenticate, and consume a pending browser login."""
        pending = pending_requests.get(request_id)
        if (
            pending is None
            or csrf_token != pending.csrf_token
            or login_csrf != pending.csrf_token
        ):
            return None
        user = self.authenticate_user(email, password)
        consumed = pending_requests.consume(request_id)
        if consumed is None:
            return None
        return consumed, user

    def create_browser_session(
        self, user_id: str, browser_sessions: BrowserSessionRepository
    ) -> str:
        return browser_sessions.create(
            user_id, settings.browser_session_lifetime_seconds
        )

    def logout_browser_session(
        self, session_id: str | None, browser_sessions: BrowserSessionRepository
    ) -> None:
        if session_id:
            browser_sessions.delete(session_id)

    def login(
        self,
        email: str,
        password: str,
        requested_scope: str | None = None,
        resource: str | None = None,
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
            extra={"requested_scope": requested_scope},
        )
        user = self._fetch_user_by_email(email)
        if user is None:
            self._logger.warning("Login failed, user not found")
            raise InvalidCredentialsException(ERROR_MESSAGE_UNAUTHORIZED)

        if not self._validate_user_password(user["id"], password):
            self._logger.warning("Login failed, invalid credentials")
            raise InvalidCredentialsException(ERROR_MESSAGE_UNAUTHORIZED)

        if resource and not self._audience_is_registered(resource):
            self._logger.warning(
                "Login failed, resource not registered",
                extra={"resource": resource, "sub": user["id"]},
            )
            raise OAuthException(
                "invalid_target",
                "The requested resource is not registered",
            )
        scope = self._derive_scope(user.get("roles", []), requested_scope)
        access_token, refresh_token = self._generate_tokens(
            user["id"], scope=scope, aud=resource
        )
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
        resource: str | None = None,
    ) -> tuple[str, int, str | None]:
        """Issue a client-credentials access token (RFC 6749 Section 4.4).

        ``resource`` is an RFC 8707 resource indicator: when given, it is
        validated against the audience registry and used as the JWT ``aud``
        claim (RFC 7519 Section 4.1.3).
        """
        self._logger.info(
            "Client credentials flow requested for client_name=%s",
            client_name,
            extra={
                "client_name": client_name,
                "requested_scope": scope,
                "requested_resource": resource,
            },
        )
        if resource:
            self._validate_audience(resource, client_name)
            aud = resource
        jwt_token = self._generate_client_credentials(
            client_name, client_secret, scope, aud
        )
        return (
            self._encode_token(jwt_token),
            settings.service_token_lifetime_seconds,
            jwt_token.scope,
        )

    def issue_token(
        self,
        body: BaseGrantRequest,
        client_name: str | None = None,
        client_secret: str | None = None,
    ) -> OAuthTokenResponse:
        """Execute a parsed OAuth token grant and build its response."""
        match body:
            case PasswordGrantRequest():
                self.validate_grant_type(body.client_id, "password")
                access_token, refresh_token, expires_in, scope = self.login(
                    body.username, body.password, body.scope, body.resource
                )
                return OAuthTokenResponse(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_in=expires_in,
                    scope=scope,
                )
            case RefreshTokenGrantRequest():
                access_token, refresh_token, expires_in, scope = self.refresh(
                    body.refresh_token
                )
                return OAuthTokenResponse(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_in=expires_in,
                    scope=scope,
                )
            case AuthorizationCodeGrantRequest():
                self.validate_grant_type(body.client_id, "authorization_code")
                access_token, refresh_token, expires_in, scope = self.exchange_code(
                    body.code,
                    body.redirect_uri,
                    body.code_verifier,
                    body.client_id,
                )
                return OAuthTokenResponse(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_in=expires_in,
                    scope=scope,
                )
            case ClientCredentialsGrantRequest():
                if client_name is None or client_secret is None:
                    raise OAuthException(
                        "invalid_client",
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        headers={"WWW-Authenticate": "Basic"},
                    )
                access_token, expires_in, scope = self.client_credentials(
                    client_name,
                    client_secret,
                    body.scope,
                    resource=body.resource,
                )
                return OAuthTokenResponse(
                    access_token=access_token,
                    expires_in=expires_in,
                    scope=scope,
                )
        raise OAuthException("unsupported_grant_type")

    def validate_grant_type(self, client_id: str | None, grant_type: str) -> None:
        """Apply an optional per-client grant allowlist."""
        if client_id is None:
            return
        client = self._service_repository.get_by_id(client_id)
        if client is not None and client.allowed_grant_types is not None:
            if grant_type not in client.allowed_grant_types:
                raise OAuthException("unauthorized_client")

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

        redirect_matches = (
            auth_code.redirect_uri == redirect_uri
            if auth_code.code_challenge
            else self._normalize_uri(auth_code.redirect_uri)
            == self._normalize_uri(redirect_uri)
        )
        if not redirect_matches:
            self._logger.warning(
                "Authorization code exchange failed, redirect_uri mismatch",
                extra={"authorization_code_id": auth_code.id},
            )
            raise OAuthException("invalid_grant")

        self._validate_pkce(auth_code, code_verifier)
        return auth_code

    def exchange_code(
        self,
        code: str,
        redirect_uri: str,
        code_verifier: str | None = None,
        client_id: str | None = None,
    ) -> tuple[str, str, int, str | None]:
        """Exchange a valid authorization code for tokens (RFC 6749 4.1.3)."""
        self._logger.info("Authorization code exchange requested")
        auth_code = self._load_auth_code(code, redirect_uri, code_verifier)
        if auth_code.code_challenge and client_id is None:
            self._logger.warning(
                "Authorization code exchange failed, client is missing"
            )
            raise OAuthException("invalid_grant")
        if client_id is not None and auth_code.client_id != client_id:
            self._logger.warning("Authorization code exchange failed, client mismatch")
            raise OAuthException("invalid_grant")

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
