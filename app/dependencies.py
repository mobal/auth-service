"""FastAPI dependency providers for the auth service.

Factory functions wired via ``Depends()`` so that services and repositories
receive their collaborators through constructor injection. This makes the
dependency graph explicit and allows tests to swap real implementations for
mocks by passing them directly to the constructor.
"""

from argon2 import PasswordHasher
from fastapi import Depends, HTTPException, Request

from app.clients.user_service_client import UserServiceClient
from app.jwt_bearer import JWTBearer
from app.models.jwt import JWTToken
from app.repositories.audience_repository import AudienceRepository
from app.repositories.authorization_code_repository import (
    AuthorizationCodeRepository,
)
from app.repositories.browser_session_repository import BrowserSessionRepository
from app.repositories.pending_authorization_request_repository import (
    PendingAuthorizationRequestRepository,
)
from app.repositories.role_scope_repository import RoleScopeRepository
from app.repositories.service_repository import ServiceRepository
from app.repositories.token_repository import TokenRepository
from app.services.auth_service import AuthService
from app.services.token_service import TokenService


def get_token_repository() -> TokenRepository:
    return TokenRepository()


def get_token_service(
    token_repository: TokenRepository = Depends(get_token_repository),
) -> TokenService:
    return TokenService(token_repository=token_repository)


def get_service_repository() -> ServiceRepository:
    return ServiceRepository()


def get_authorization_code_repository() -> AuthorizationCodeRepository:
    return AuthorizationCodeRepository()


def get_browser_session_repository() -> BrowserSessionRepository:
    return BrowserSessionRepository()


def get_pending_authorization_request_repository() -> (
    PendingAuthorizationRequestRepository
):
    return PendingAuthorizationRequestRepository()


def get_role_scope_repository() -> RoleScopeRepository:
    return RoleScopeRepository()


def get_password_hasher() -> PasswordHasher:
    return PasswordHasher()


def get_user_service_client() -> UserServiceClient:
    return UserServiceClient()


def get_audience_repository() -> AudienceRepository:
    return AudienceRepository()


def get_auth_service(
    password_hasher: PasswordHasher = Depends(get_password_hasher),
    token_service: TokenService = Depends(get_token_service),
    service_repository: ServiceRepository = Depends(get_service_repository),
    authorization_code_repository: AuthorizationCodeRepository = Depends(
        get_authorization_code_repository
    ),
    user_service_client: UserServiceClient = Depends(get_user_service_client),
    role_scope_repository: RoleScopeRepository = Depends(get_role_scope_repository),
    audience_repository: AudienceRepository = Depends(get_audience_repository),
) -> AuthService:
    return AuthService(
        password_hasher=password_hasher,
        token_service=token_service,
        service_repository=service_repository,
        authorization_code_repository=authorization_code_repository,
        user_service_client=user_service_client,
        role_scope_repository=role_scope_repository,
        audience_repository=audience_repository,
    )


def get_jwt_bearer(
    request: Request,
    token_service: TokenService = Depends(get_token_service),
) -> JWTToken:
    """Resolve the request's bearer token into a validated :class:`JWTToken`.

    Returns the JWTBearer result (not the JWTBearer instance itself) so that
    FastAPI injects the decoded token into route handlers.
    """
    token = JWTBearer(token_service=token_service)(request)
    if token is None:
        raise HTTPException(status_code=403, detail="Not authenticated")
    return token


def get_optional_jwt_bearer(
    request: Request,
    token_service: TokenService = Depends(get_token_service),
) -> JWTToken | None:
    return JWTBearer(token_service=token_service, auto_error=False)(request)
