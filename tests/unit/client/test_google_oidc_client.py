import json
from types import SimpleNamespace

import jwt
import pybreaker
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.clients.google_oidc_client import GoogleOIDCClient
from app.exceptions import GoogleOIDCValidationError


@pytest.fixture(autouse=True)
def clear_metadata_cache():
    GoogleOIDCClient._metadata_cache = None
    GoogleOIDCClient._metadata_expires_at = 0.0


class TestGoogleOIDCClient:
    @pytest.fixture
    def client(self) -> GoogleOIDCClient:
        return GoogleOIDCClient()

    def test_discovery_is_cached(self, mocker, client: GoogleOIDCClient):
        response = SimpleNamespace(
            status_code=200,
            json=lambda: {
                "issuer": "https://accounts.google.com",
                "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_endpoint": "https://oauth2.googleapis.com/token",
                "jwks_uri": "https://www.googleapis.com/oauth2/v3/certs",
            },
            raise_for_status=mocker.Mock(),
        )
        get = mocker.patch.object(client._client, "get", return_value=response)

        first_metadata = client.get_metadata()
        second_metadata = client.get_metadata()

        assert first_metadata is second_metadata
        assert str(first_metadata.issuer) == "https://accounts.google.com/"
        assert (
            str(first_metadata.authorization_endpoint)
            == "https://accounts.google.com/o/oauth2/v2/auth"
        )
        get.assert_called_once()

    def test_discovery_rejects_unexpected_issuer(
        self, mocker, client: GoogleOIDCClient
    ):
        response = SimpleNamespace(
            status_code=200,
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

    def test_discovery_opens_circuit_after_upstream_failure(
        self, httpx2_mock, client: GoogleOIDCClient
    ):
        client._breaker = pybreaker.CircuitBreaker(fail_max=1, reset_timeout=60)
        url = "https://accounts.google.com/.well-known/openid-configuration"
        httpx2_mock.add_response(method="GET", url=url, status_code=503)

        with pytest.raises(pybreaker.CircuitBreakerError):
            client.get_metadata()

        with pytest.raises(pybreaker.CircuitBreakerError):
            client.get_metadata()

        assert len(httpx2_mock.get_requests()) == 1

    def test_request_rejects_unsupported_method(self, client: GoogleOIDCClient):
        with pytest.raises(ValueError, match="Unsupported HTTP method"):
            client._request("PUT", "https://accounts.google.com")

    def test_discovery_cache_is_checked_again_inside_lock(
        self, mocker, monkeypatch, client: GoogleOIDCClient
    ):
        metadata = SimpleNamespace(
            issuer="https://accounts.google.com",
            authorization_endpoint="https://accounts.google.com/auth",
            token_endpoint="https://oauth2.googleapis.com/token",
            jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
        )
        monkeypatch.setattr(GoogleOIDCClient, "_metadata_cache", metadata)
        monkeypatch.setattr(GoogleOIDCClient, "_metadata_expires_at", 1.0)
        mocker.patch(
            "app.clients.google_oidc_client.time.monotonic", side_effect=[0.0, 2.0]
        )
        get = mocker.patch.object(client._client, "get")

        assert client.get_metadata() == metadata
        get.assert_not_called()

    @pytest.mark.parametrize(
        "token", ["not-a-jwt", jwt.encode({}, "secret", algorithm="HS256")]
    )
    def test_validate_id_token_rejects_unsupported_token_header(
        self, client: GoogleOIDCClient, token: str
    ):
        with pytest.raises(GoogleOIDCValidationError):
            client.validate_id_token(token, "nonce")

    def test_validate_id_token_rejects_missing_signing_key(
        self, mocker, client: GoogleOIDCClient
    ):
        client.get_metadata = mocker.Mock(
            return_value=SimpleNamespace(jwks_uri="https://google.test/jwks")
        )
        client._breaker.call = mocker.Mock(
            return_value=SimpleNamespace(
                json=lambda: {"keys": []}, raise_for_status=mocker.Mock()
            )
        )
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        token = jwt.encode(
            {"iss": "https://accounts.google.com", "sub": "subject"},
            private_key,
            algorithm="RS256",
            headers={"kid": "missing", "alg": "RS256"},
        )

        with pytest.raises(GoogleOIDCValidationError, match="signing key"):
            client.validate_id_token(token, "nonce")

    def test_validate_id_token_accepts_signed_verified_identity(
        self, mocker, client: GoogleOIDCClient
    ):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        id_token = jwt.encode(
            {
                "iss": "https://accounts.google.com",
                "sub": "google-subject",
                "aud": "test-google-client-id",
                "exp": 2_000_000_000,
                "nonce": "expected-nonce",
                "email": "root@squarelabs.hu",
                "email_verified": True,
            },
            private_key,
            algorithm="RS256",
            headers={"kid": "google-key"},
        )
        client.get_metadata = mocker.Mock(
            return_value=SimpleNamespace(jwks_uri="https://google.test/jwks")
        )
        jwk = {
            **json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key())),
            "kid": "google-key",
        }
        jwks_response = SimpleNamespace(
            json=lambda: {"keys": [jwk]},
            raise_for_status=mocker.Mock(),
        )
        client._breaker.call = mocker.Mock(return_value=jwks_response)

        identity = client.validate_id_token(id_token, "expected-nonce")

        assert identity.email == "root@squarelabs.hu"
        assert identity.subject == "google-subject"

    def test_validate_id_token_rejects_nonce_mismatch(
        self, mocker, client: GoogleOIDCClient
    ):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        id_token = jwt.encode(
            {
                "iss": "https://accounts.google.com",
                "sub": "google-subject",
                "aud": "test-google-client-id",
                "exp": 2_000_000_000,
                "nonce": "token-nonce",
                "email": "root@squarelabs.hu",
                "email_verified": True,
            },
            private_key,
            algorithm="RS256",
            headers={"kid": "google-key"},
        )
        client.get_metadata = mocker.Mock(
            return_value=SimpleNamespace(jwks_uri="https://google.test/jwks")
        )
        jwk = {
            **json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key())),
            "kid": "google-key",
        }
        client._breaker.call = mocker.Mock(
            return_value=SimpleNamespace(
                json=lambda: {"keys": [jwk]}, raise_for_status=mocker.Mock()
            )
        )

        with pytest.raises(GoogleOIDCValidationError, match="nonce mismatch"):
            client.validate_id_token(id_token, "different-nonce")
