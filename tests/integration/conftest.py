import pytest

@pytest.fixture
def base_url() -> str:
    return "api/v1"

@pytest.fixture
def login_url(base_url: str) -> str:
    return f"{base_url}/login"

@pytest.fixture
def refresh_url(base_url: str) -> str:
    return f"{base_url}/refresh"
