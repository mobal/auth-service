from types import SimpleNamespace

import pytest

from app.clients.google_oidc_client import GoogleOIDCClient


@pytest.fixture(autouse=True)
def clear_metadata_cache():
    GoogleOIDCClient._metadata_cache = None
    GoogleOIDCClient._metadata_expires_at = 0.0


def test_discovery_is_cached(mocker):
    client = GoogleOIDCClient()
    response = SimpleNamespace(
        json=lambda: {
            "issuer": "https://accounts.google.com",
            "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_endpoint": "https://oauth2.googleapis.com/token",
            "jwks_uri": "https://www.googleapis.com/oauth2/v3/certs",
        },
        raise_for_status=mocker.Mock(),
    )
    get = mocker.patch.object(client._client, "get", return_value=response)

    assert client.get_metadata() == client.get_metadata()
    get.assert_called_once()


def test_discovery_rejects_unexpected_issuer(mocker):
    client = GoogleOIDCClient()
    response = SimpleNamespace(
        json=lambda: {
            "issuer": "https://evil.example",
            "authorization_endpoint": "https://evil.example/auth",
            "token_endpoint": "https://evil.example/token",
            "jwks_uri": "https://evil.example/jwks",
        },
        raise_for_status=mocker.Mock(),
    )
    mocker.patch.object(client._client, "get", return_value=response)

    with pytest.raises(ValueError, match="unexpected issuer"):
        client.get_metadata()
