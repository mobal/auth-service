import boto3
import pytest
from moto import mock_dynamodb

from app.services import CacheService
from app.settings import Settings


@pytest.fixture
def cache_service() -> CacheService:
    return CacheService()


@pytest.fixture
def dynamodb_resource():
    with mock_dynamodb():
        yield boto3.resource('dynamodb', region_name='eu-central-1', aws_access_key_id='aws-access-key-id',
                             aws_access_key_secret='aws-access-key-secret')


@pytest.fixture(autouse=True)
def set_environment_variables(monkeypatch):
    monkeypatch.setenv('APP_NAME', 'auth-service')
    monkeypatch.setenv('APP_STAGE', 'test')
    monkeypatch.setenv('APP_TIMEZONE', 'Europe/Budapest')


@pytest.fixture
def settings() -> Settings:
    return Settings()
