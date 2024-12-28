import uuid

import pendulum
import pytest as pytest

from app.jwt_bearer import JWTBearer
from app.models import User
from app.repositories import TokenRepository, UserRepository
from app.services import CacheService, JWTToken, TokenService


@pytest.fixture
def cache_service() -> CacheService:
    return CacheService()


@pytest.fixture
def jwt_bearer() -> JWTBearer:
    return JWTBearer()


@pytest.fixture
def jwt_token(user_model) -> JWTToken:
    iat = pendulum.now()
    exp = iat.add(hours=1)
    return JWTToken(
        exp=exp.int_timestamp,
        iat=iat.int_timestamp,
        iss=None,
        jti=str(uuid.uuid4()),
        sub=user_model,
    )


@pytest.fixture
def token_repository() -> TokenRepository:
    return TokenRepository()


@pytest.fixture
def token_service() -> TokenService:
    return TokenService()


@pytest.fixture
def user_model() -> User:
    return User(
        id=str(uuid.uuid4()),
        display_name="root",
        email="root@netcode.hu",
        password="password",
        roles=["root"],
        username="root",
        created_at=pendulum.now().to_iso8601_string(),
    )


@pytest.fixture
def user_repository() -> UserRepository:
    return UserRepository()
