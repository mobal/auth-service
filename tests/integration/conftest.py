import pytest


@pytest.fixture
def base_url() -> str:
    return "api/v1"


@pytest.fixture
def token_url(base_url: str) -> str:
    return f"{base_url}/oauth/token"


@pytest.fixture
def revoke_url(base_url: str) -> str:
    return f"{base_url}/oauth/revoke"
