from datetime import UTC, datetime
from typing import Any

import pytest

from app.jwt_bearer import JWTBearer
from app.models.jwt import JWTToken, RefreshToken
from app.repositories.service_repository import ServiceRepository
from app.repositories.token_repository import TokenRepository
from app.services.token_service import TokenService


@pytest.fixture
def jwt_bearer(token_service: TokenService) -> JWTBearer:
    return JWTBearer(token_service=token_service)


@pytest.fixture
def service_repository() -> ServiceRepository:
    return ServiceRepository()


@pytest.fixture
def token(jwt_token: JWTToken, refresh_token: RefreshToken) -> dict[str, Any]:
    return {
        "jti": jwt_token.jti,
        "jwt_token": jwt_token.model_dump(),
        "refresh_token": refresh_token.token,
        "created_at": datetime.fromtimestamp(jwt_token.iat, tz=UTC).isoformat(),
        "expire_at": datetime.fromtimestamp(refresh_token.ttl, tz=UTC).isoformat(),
        "ttl": refresh_token.ttl,
    }


@pytest.fixture
def token_repository() -> TokenRepository:
    return TokenRepository()


@pytest.fixture
def token_service(token_repository: TokenRepository) -> TokenService:
    return TokenService(token_repository=token_repository)
