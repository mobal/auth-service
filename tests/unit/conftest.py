from typing import Any
from unittest.mock import ANY

import pytest as pytest

from app.jwt_bearer import JWTBearer
from app.models.jwt import JWTToken
from app.repositories.token_repository import TokenRepository
from app.repositories.user_repository import UserRepository
from app.services.token_service import TokenService


@pytest.fixture
def jwt_bearer() -> JWTBearer:
    return JWTBearer()


@pytest.fixture
def token(jwt_token: JWTToken, refresh_token: str) -> dict[str, Any]:
    return {
        "jti": jwt_token.jti,
        "jwt_token": jwt_token.model_dump(),
        "refresh_token": refresh_token,
        "created_at": ANY,
        "ttl": jwt_token.exp,
    }


@pytest.fixture
def token_repository() -> TokenRepository:
    return TokenRepository()


@pytest.fixture
def token_service() -> TokenService:
    return TokenService()


@pytest.fixture
def user_repository() -> UserRepository:
    return UserRepository()
