import pytest

from app.settings import Settings


@pytest.fixture(autouse=True)
def set_environment_variables(monkeypatch):
    monkeypatch.setenv('APP_NAME', 'auth-service')
    monkeypatch.setenv('APP_STAGE', 'test')
    monkeypatch.setenv('APP_TIMEZONE', 'Europe/Budapest')
    monkeypatch.setenv('JWT_SECRET', 'p2s5v8y/B?E(H+MbPeShVmYq3t6w9z$C')
    monkeypatch.setenv('JWT_TOKEN_LIFETIME', '3600')
    monkeypatch.setenv('CACHE_SERVICE_BASE_URL', 'https://localhost')


@pytest.fixture
def settings() -> Settings:
    return Settings()
