import uuid

import boto3
import pendulum
import pytest as pytest
from moto import mock_dynamodb

from app.auth import JWTBearer
from app.models import JWTToken, User
from app.services import CacheService


@pytest.fixture
def cache_service() -> CacheService:
    return CacheService()


@pytest.fixture
def dynamodb_resource():
    with mock_dynamodb():
        yield boto3.resource('dynamodb', region_name='eu-central-1', aws_access_key_id='aws-access-key-id',
                             aws_access_key_secret='aws-access-key-secret')


@pytest.fixture
def jwt_bearer() -> JWTBearer:
    return JWTBearer()


@pytest.fixture
def jwt_token(user) -> JWTToken:
    iat = pendulum.now()
    exp = iat.add(hours=1)
    return JWTToken(
        exp=exp.int_timestamp,
        iat=iat.int_timestamp,
        jti=str(uuid.uuid4()),
        sub=user
    )


@pytest.fixture
def user() -> User:
    return User(
        id=str(uuid.uuid4()),
        display_name='root',
        email='root@netcode.hu',
        password='password',
        roles=['root'],
        username='root',
        created_at=pendulum.now().to_iso8601_string()
    )
