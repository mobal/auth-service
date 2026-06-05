"""FastAPI dependency providers for the auth service.

Factory functions wired via ``Depends()`` so that services and repositories
receive their collaborators through constructor injection. This makes the
dependency graph explicit and allows tests to swap real implementations for
mocks by passing them directly to the constructor.
"""

from fastapi import Depends

from app.clients.user_service_client import UserServiceClient
from app.jwt_bearer import JWTBearer
from app.repositories.authorization_code_repository import (
    AuthorizationCodeRepository,
)
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


def get_user_service_client() -> UserServiceClient:
    return UserServiceClient()


def get_auth_service(
    token_service: TokenService = Depends(get_token_service),
    service_repository: ServiceRepository = Depends(get_service_repository),
    authorization_code_repository: AuthorizationCodeRepository = Depends(
        get_authorization_code_repository
    ),
    user_service_client: UserServiceClient = Depends(get_user_service_client),
) -> AuthService:
    return AuthService(
        token_service=token_service,
        service_repository=service_repository,
        authorization_code_repository=authorization_code_repository,
        user_service_client=user_service_client,
    )


def get_jwt_bearer(
    token_service: TokenService = Depends(get_token_service),
) -> JWTBearer:
    return JWTBearer(token_service=token_service)
