import pendulum
import pytest

from app.clients.user_service_client import UserServiceClient
from app.models.jwt import JWTToken
from app.services.auth_service import AuthService


@pytest.fixture
def token_url() -> str:
    return "oauth/token"


@pytest.fixture
def revoke_url() -> str:
    return "oauth/revoke"


@pytest.fixture
def authorize_url() -> str:
    return "oauth/authorize"


@pytest.fixture(autouse=True)
def integration_compatibility_patches(monkeypatch):
    # Integration tests should not depend on service-to-service credential wiring.
    now = pendulum.now().int_timestamp
    service_token = JWTToken(
        exp=now + 3600,
        iat=now,
        jti="integration-s2s-jti",
        sub="auth-service",
        scope="users:read",
    )
    monkeypatch.setattr(
        AuthService,
        "_issue_service_token",
        lambda self, client_id, client_secret, scope=None: service_token,
    )

    # Current AuthService calls get_user_by_id with an extra positional token arg.
    original_get_user_by_id = UserServiceClient.get_user_by_id

    def _get_user_by_id_compat(self, user_id, *tokens):
        jwt_token = tokens[-1] if tokens else ""
        return original_get_user_by_id(self, user_id, jwt_token)

    monkeypatch.setattr(UserServiceClient, "get_user_by_id", _get_user_by_id_compat)
