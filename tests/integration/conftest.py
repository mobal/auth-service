import pytest


@pytest.fixture
def token_url() -> str:
    return "oauth/token"


@pytest.fixture
def revoke_url() -> str:
    return "oauth/revoke"


@pytest.fixture
def authorize_url() -> str:
    return "oauth/authorize"
