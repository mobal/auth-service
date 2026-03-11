from typing import Any

import pendulum
import pytest as pytest

from app.jwt_bearer import JWTBearer
from app.models.jwt import JWTToken, RefreshToken
from app.repositories.service_repository import ServiceRepository
from app.repositories.token_repository import TokenRepository
from app.services.token_service import TokenService


@pytest.fixture
def jwt_bearer() -> JWTBearer:
    return JWTBearer()


@pytest.fixture
def service_repository() -> ServiceRepository:
    return ServiceRepository()


@pytest.fixture
def token(jwt_token: JWTToken, refresh_token: RefreshToken) -> dict[str, Any]:
    return {
        "jti": jwt_token.jti,
        "jwt_token": jwt_token.model_dump(),
        "refresh_token": refresh_token.token,
        "created_at": pendulum.from_timestamp(jwt_token.iat).to_iso8601_string(),
        "expire_at": pendulum.from_timestamp(refresh_token.ttl).to_iso8601_string(),
        "ttl": refresh_token.ttl,
    }


@pytest.fixture
def token_repository() -> TokenRepository:
    return TokenRepository()


@pytest.fixture
def token_service() -> TokenService:
    return TokenService()
