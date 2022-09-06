import pytest

from app.settings import Settings


@pytest.fixture(autouse=True)
def set_environment_variables(monkeypatch):
    monkeypatch.setenv('APP_DEBUG', 'true')
    monkeypatch.setenv('APP_NAME', 'auth-service')
    monkeypatch.setenv('APP_STAGE', 'test')
    monkeypatch.setenv('APP_TIMEZONE', 'Europe/Budapest')

    monkeypatch.setenv('AWS_REGION_NAME', 'eu-central-1')
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'aws_access_key_id')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'aws_secret_access_key')

    monkeypatch.setenv('JWT_SECRET', 'jWRhsrF7Puk575uA7jH34CvF6Agj5UAO')
    monkeypatch.setenv('JWT_TOKEN_LIFETIME', '3600')
    monkeypatch.setenv('CACHE_SERVICE_BASE_URL', 'https://localhost')


@pytest.fixture
def settings() -> Settings:
    return Settings()
