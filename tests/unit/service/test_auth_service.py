import uuid
from types import SimpleNamespace
from unittest.mock import ANY

import jwt
import pendulum
import pytest as pytest
from fastapi import HTTPException, status

from app.clients.user_service_client import UserServiceClient
from app.exceptions import (
    OAuthException,
    TokenNotFoundException,
    UserNotFoundException,
)
from app.models.jwt import JWTToken, RefreshToken
from app.models.service import ServiceCredential
from app.services.auth_service import AuthService
from app.services.token_service import TokenService
from app.settings import Settings

ALGORITHMS = ["HS256"]


class TestAuthService:
    @pytest.fixture(autouse=True)
    def _patch_auth_service_dependencies(self, mocker, monkeypatch, settings: Settings):
        # AuthService now expects this setting when requesting a user-service token.
        patched_settings = SimpleNamespace(
            service_token_secret="test-service-token-secret"
        )
        for key, value in settings.model_dump().items():
            setattr(patched_settings, key, value)
        patched_settings.jwt_secret = settings.jwt_secret
        patched_settings.user_service_base_url = settings.user_service_base_url

        monkeypatch.setattr("app.services.auth_service.settings", patched_settings)
        now = pendulum.now().int_timestamp
        service_token = JWTToken(
            exp=now + 3600,
            iat=now,
            jti="unit-s2s-jti",
            sub="auth-service",
            scope="users:read",
        )
        mocker.patch.object(
            AuthService, "_issue_service_token", return_value=service_token
        )

    @pytest.fixture
    def auth_service(self) -> AuthService:
        return AuthService()

    def test_successfully_login(
        self,
        mocker,
        auth_service: AuthService,
        user_data: dict,
        settings: Settings,
        token_service: TokenService,
    ):
        mocker.patch.object(
            UserServiceClient, "get_user_by_email", return_value=user_data
        )
        mocker.patch.object(
            UserServiceClient, "validate_user_password", return_value=True
        )
        mocker.patch.object(TokenService, "create")

        jwt_str, _, _, _ = auth_service.login(user_data["email"], "password")
        decoded = JWTToken(**jwt.decode(jwt_str, settings.jwt_secret, ALGORITHMS))

        assert decoded.sub == user_data["id"]
        assert (
            pendulum.from_timestamp(decoded.exp) - pendulum.from_timestamp(decoded.iat)
        ).in_words() == "1 hour"
        auth_service._user_service_client.get_user_by_email.assert_called_once_with(
            user_data["email"], ANY
        )
        auth_service._user_service_client.validate_user_password.assert_called_once_with(
            user_data["id"], "password", ANY
        )
        token_service.create.assert_called_once_with(decoded, ANY)

    def test_fail_to_login_due_to_invalid_credentials(
        self,
        mocker,
        auth_service: AuthService,
    ):
        mocker.patch.object(UserServiceClient, "get_user_by_email", return_value=None)
        mocker.patch.object(
            UserServiceClient, "validate_user_password", return_value=True
        )

        with pytest.raises(HTTPException) as excinfo:
            auth_service.login("user@example.com", "wrong_password")

        assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert excinfo.value.detail == "Unauthorized"
        auth_service._user_service_client.validate_user_password.assert_not_called()

    def test_fail_to_login_due_to_wrong_password(
        self,
        mocker,
        auth_service: AuthService,
        user_data: dict,
    ):
        mocker.patch.object(
            UserServiceClient, "get_user_by_email", return_value=user_data
        )
        mocker.patch.object(
            UserServiceClient, "validate_user_password", return_value=False
        )

        with pytest.raises(HTTPException) as excinfo:
            auth_service.login(user_data["email"], "wrong_password")

        assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert excinfo.value.detail == "Unauthorized"

    def test_successfully_logout(
        self,
        mocker,
        auth_service: AuthService,
        jwt_token: JWTToken,
        token_service: TokenService,
    ):
        mocker.patch.object(TokenService, "delete_by_id")

        auth_service.logout(jwt_token)

        token_service.delete_by_id.assert_called_once_with(jwt_token.jti)

    def test_fail_to_logout_due_to_token_service_exception(
        self,
        mocker,
        auth_service: AuthService,
        jwt_token: JWTToken,
        token_service: TokenService,
    ):
        error_message = "The requested token was not found"
        mocker.patch.object(
            TokenService,
            "delete_by_id",
            side_effect=TokenNotFoundException(error_message),
        )

        with pytest.raises(TokenNotFoundException) as excinfo:
            auth_service.logout(jwt_token)

        assert status.HTTP_404_NOT_FOUND == excinfo.value.status_code
        assert error_message == excinfo.value.detail
        token_service.delete_by_id.assert_called_once_with(jwt_token.jti)

    def test_successfully_refresh_tokens(
        self,
        mocker,
        auth_service: AuthService,
        jwt_secret_ssm_param_value: str,
        jwt_token: JWTToken,
        refresh_token: RefreshToken,
        token_service: TokenService,
    ):
        item = {
            "jti": jwt_token.jti,
            "jwt_token": jwt_token.model_dump(),
            "refresh_token": refresh_token.token,
            "created_at": pendulum.now().to_iso8601_string(),
            "expire_at": pendulum.from_timestamp(refresh_token.ttl).to_iso8601_string(),
            "ttl": jwt_token.exp,
        }
        mocker.patch.object(TokenService, "get_by_refresh_token", return_value=item)
        mocker.patch.object(TokenService, "create")
        mocker.patch.object(TokenService, "delete_by_id")

        new_jwt_token, _, _, _ = auth_service.refresh(refresh_token)

        token_service.get_by_refresh_token.assert_called_once_with(refresh_token)
        token_service.create.assert_called_once_with(
            JWTToken(
                **jwt.decode(
                    new_jwt_token,
                    jwt_secret_ssm_param_value,
                    algorithms=["HS256"],
                )
            ),
            ANY,
        )
        token_service.delete_by_id.assert_called_once_with(jwt_token.jti)

    def test_fail_to_refresh_due_to_missing_token(
        self,
        mocker,
        auth_service: AuthService,
        refresh_token: str,
        token_service: TokenService,
    ):
        mocker.patch.object(TokenService, "get_by_refresh_token", return_value=None)

        with pytest.raises(TokenNotFoundException) as excinfo:
            auth_service.refresh(refresh_token)

        assert TokenNotFoundException.__name__ == excinfo.typename
        assert "The requested token was not found" == excinfo.value.detail

        token_service.get_by_refresh_token.assert_called_once_with(refresh_token)

    def test_successfully_refresh_revokes_stored_jti(
        self,
        mocker,
        auth_service: AuthService,
        refresh_token: RefreshToken,
        token_service: TokenService,
    ):
        stored_jti = str(uuid.uuid4())
        now = pendulum.now().int_timestamp
        item = {
            "jti": stored_jti,
            "jwt_token": {
                "exp": now,
                "iat": now,
                "iss": None,
                "jti": stored_jti,
                "sub": "user-1",
            },
            "refresh_token": refresh_token.token,
            "created_at": pendulum.now().to_iso8601_string(),
            "ttl": now + 3600,
        }
        mocker.patch.object(TokenService, "get_by_refresh_token", return_value=item)
        mocker.patch.object(TokenService, "create")
        mocker.patch.object(TokenService, "delete_by_id")

        auth_service.refresh(refresh_token.token)

        token_service.delete_by_id.assert_called_once_with(stored_jti)
        token_service.get_by_refresh_token.assert_called_once_with(refresh_token.token)

    def test_fail_to_refresh_due_to_expired_token(
        self,
        mocker,
        auth_service: AuthService,
        refresh_token: str,
        token_service: TokenService,
    ):
        from app.exceptions import TokenExpiredException

        expired_time = pendulum.now().subtract(days=1).int_timestamp
        now = pendulum.now().int_timestamp
        item = {
            "jti": str(uuid.uuid4()),
            "jwt_token": {
                "exp": now,
                "iat": now,
                "iss": None,
                "jti": str(uuid.uuid4()),
                "sub": "user-1",
            },
            "refresh_token": refresh_token,
            "created_at": pendulum.now().to_iso8601_string(),
            "ttl": expired_time,
        }
        mocker.patch.object(TokenService, "get_by_refresh_token", return_value=item)

        with pytest.raises(TokenExpiredException) as excinfo:
            auth_service.refresh(refresh_token)

        assert TokenExpiredException.__name__ == excinfo.typename
        assert status.HTTP_401_UNAUTHORIZED == excinfo.value.status_code
        assert "The requested token has expired" == excinfo.value.detail

        token_service.get_by_refresh_token.assert_called_once_with(refresh_token)

    def test_successfully_derive_scope_without_request(self, auth_service: AuthService):
        scope = auth_service._derive_scope(["root"], None)

        assert scope == "tokens:revoke users:read users:write"

    def test_successfully_derive_scope_with_valid_request(
        self, auth_service: AuthService
    ):
        scope = auth_service._derive_scope(["root"], "users:read")

        assert scope == "users:read"

    def test_fail_to_derive_scope_due_to_invalid_scope(self, auth_service: AuthService):
        with pytest.raises(OAuthException) as excinfo:
            auth_service._derive_scope(["root"], "admin:all")

        assert excinfo.value.oauth_error == "invalid_scope"

    def test_successfully_client_credentials_without_requested_scope(
        self,
        mocker,
        auth_service: AuthService,
        password: str,
        service_credential: ServiceCredential,
        settings: Settings,
    ):
        mocker.patch(
            "app.services.auth_service.ServiceRepository.get_by_name",
            return_value=service_credential,
        )
        mocker.patch.object(TokenService, "create")

        token, expires_in, scope = auth_service.client_credentials(
            service_credential.name, password, None
        )
        decoded = JWTToken(
            **jwt.decode(token, settings.jwt_secret, algorithms=ALGORITHMS)
        )

        assert decoded.sub == service_credential.name
        assert decoded.scope == scope
        assert expires_in == settings.service_token_lifetime
        assert scope == "users:read users:write"
        auth_service._token_service.create.assert_called_once()

    def test_successfully_client_credentials_with_requested_scope(
        self,
        mocker,
        auth_service: AuthService,
        password: str,
        service_credential: ServiceCredential,
    ):
        mocker.patch(
            "app.services.auth_service.ServiceRepository.get_by_name",
            return_value=service_credential,
        )
        mocker.patch.object(TokenService, "create")

        _, _, scope = auth_service.client_credentials(
            service_credential.name, password, "users:read"
        )

        assert scope == "users:read"
        auth_service._token_service.create.assert_called_once()

    def test_fail_to_client_credentials_due_to_missing_service(
        self, mocker, auth_service: AuthService
    ):
        mocker.patch(
            "app.services.auth_service.ServiceRepository.get_by_name",
            return_value=None,
        )

        with pytest.raises(OAuthException) as excinfo:
            auth_service.client_credentials("missing", "secret", None)

        assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert excinfo.value.oauth_error == "invalid_client"

    def test_fail_to_client_credentials_due_to_invalid_secret(
        self,
        mocker,
        auth_service: AuthService,
        password: str,
        service_credential: ServiceCredential,
    ):
        mocker.patch(
            "app.services.auth_service.ServiceRepository.get_by_name",
            return_value=service_credential,
        )

        with pytest.raises(OAuthException) as excinfo:
            auth_service.client_credentials(
                service_credential.name, "wrong-secret", None
            )

        assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert excinfo.value.oauth_error == "invalid_client"

    def test_fail_to_client_credentials_due_to_invalid_scope(
        self,
        mocker,
        auth_service: AuthService,
        password: str,
        service_credential: ServiceCredential,
    ):
        mocker.patch(
            "app.services.auth_service.ServiceRepository.get_by_name",
            return_value=service_credential,
        )

        with pytest.raises(OAuthException) as excinfo:
            auth_service.client_credentials(
                service_credential.name, password, "tokens:revoke"
            )

        assert excinfo.value.oauth_error == "invalid_scope"

    def test_successfully_authorize_with_user(
        self,
        mocker,
        auth_service: AuthService,
        user_data: dict,
    ):
        mocker.patch.object(UserServiceClient, "get_user_by_id", return_value=user_data)
        create_mock = mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.create",
            return_value="test_code_123",
        )

        code = auth_service.authorize(
            user_id=user_data["id"],
            client_id="client_123",
            redirect_uri="https://example.com/callback",
            requested_scope="users:read",
        )

        assert code == "test_code_123"
        create_mock.assert_called_once()
        call_kwargs = create_mock.call_args[1]
        assert call_kwargs["client_id"] == "client_123"
        assert call_kwargs["user_id"] == user_data["id"]
        assert call_kwargs["redirect_uri"] == "https://example.com/callback"
        assert call_kwargs["scope"] == "users:read"
        assert call_kwargs["code_challenge"] is None
        assert call_kwargs["code_challenge_method"] is None

    def test_successfully_authorize_with_pkce_s256(
        self,
        mocker,
        auth_service: AuthService,
        user_data: dict,
    ):
        mocker.patch.object(UserServiceClient, "get_user_by_id", return_value=user_data)
        create_mock = mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.create",
            return_value="test_code_pkce",
        )

        code = auth_service.authorize(
            user_id=user_data["id"],
            client_id="client_123",
            redirect_uri="https://example.com/callback",
            requested_scope="users:read",
            code_challenge="E9Mrozoa2owUG2gw61pfAqgxVrQj5zwJckeqyUmKkqM",
            code_challenge_method="S256",
        )

        assert code == "test_code_pkce"
        call_kwargs = create_mock.call_args[1]
        assert (
            call_kwargs["code_challenge"]
            == "E9Mrozoa2owUG2gw61pfAqgxVrQj5zwJckeqyUmKkqM"
        )
        assert call_kwargs["code_challenge_method"] == "S256"

    def test_successfully_authorize_with_pkce_plain(
        self,
        mocker,
        auth_service: AuthService,
        user_data: dict,
    ):
        mocker.patch.object(UserServiceClient, "get_user_by_id", return_value=user_data)
        create_mock = mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.create",
            return_value="test_code_plain",
        )

        code = auth_service.authorize(
            user_id=user_data["id"],
            client_id="client_123",
            redirect_uri="https://example.com/callback",
            code_challenge="test_challenge_plain",
            code_challenge_method="plain",
        )

        assert code == "test_code_plain"
        call_kwargs = create_mock.call_args[1]
        assert call_kwargs["code_challenge"] == "test_challenge_plain"
        assert call_kwargs["code_challenge_method"] == "plain"

    def test_fail_to_authorize_due_to_user_not_found(
        self,
        mocker,
        auth_service: AuthService,
    ):
        mocker.patch.object(UserServiceClient, "get_user_by_id", return_value=None)

        with pytest.raises(UserNotFoundException) as excinfo:
            auth_service.authorize(
                user_id="nonexistent_user",
                client_id="client_123",
                redirect_uri="https://example.com/callback",
            )

        assert "not found" in str(excinfo.value.detail).lower()

    def test_successfully_exchange_code_without_pkce(
        self,
        mocker,
        auth_service: AuthService,
        user_data: dict,
    ):
        auth_code = mocker.MagicMock()
        auth_code.id = "auth-code-id-123"
        auth_code.code = "auth_code_123"
        auth_code.user_id = user_data["id"]
        auth_code.redirect_uri = "https://example.com/callback"
        auth_code.scope = "users:read"
        auth_code.code_challenge = None
        auth_code.ttl = pendulum.now().add(minutes=5).int_timestamp

        mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.get_by_code",
            return_value=auth_code,
        )
        mocker.patch.object(UserServiceClient, "get_user_by_id", return_value=user_data)
        mocker.patch("app.services.auth_service.TokenService.create")
        consume_mock = mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.consume_by_id",
            return_value=True,
        )

        jwt_str, refresh_token, exp, scope = auth_service.exchange_code(
            code="auth_code_123",
            redirect_uri="https://example.com/callback",
        )

        assert jwt_str is not None
        assert refresh_token is not None
        assert exp == 3600
        assert scope == "users:read"
        consume_mock.assert_called_once_with("auth-code-id-123")

    def test_fail_to_exchange_code_due_to_invalid_code(
        self,
        mocker,
        auth_service: AuthService,
    ):
        mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.get_by_code",
            return_value=None,
        )

        with pytest.raises(OAuthException) as excinfo:
            auth_service.exchange_code(
                code="invalid_code",
                redirect_uri="https://example.com/callback",
            )

        assert excinfo.value.oauth_error == "invalid_grant"

    def test_fail_to_exchange_code_due_to_expired_code(
        self,
        mocker,
        auth_service: AuthService,
    ):
        auth_code = mocker.MagicMock()
        auth_code.id = "expired-code-id"
        auth_code.code = "auth_code_123"
        auth_code.redirect_uri = "https://example.com/callback"
        auth_code.code_challenge = None
        auth_code.ttl = pendulum.now().subtract(minutes=5).int_timestamp

        mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.get_by_code",
            return_value=auth_code,
        )
        consume_mock = mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.consume_by_id",
            return_value=True,
        )

        with pytest.raises(OAuthException) as excinfo:
            auth_service.exchange_code(
                code="auth_code_123",
                redirect_uri="https://example.com/callback",
            )

        assert excinfo.value.oauth_error == "invalid_grant"
        consume_mock.assert_called_once_with("expired-code-id")

    def test_fail_to_exchange_code_due_to_redirect_uri_mismatch(
        self,
        mocker,
        auth_service: AuthService,
    ):
        auth_code = mocker.MagicMock()
        auth_code.id = "auth-code-id"
        auth_code.code = "auth_code_123"
        auth_code.redirect_uri = "https://example.com/callback"
        auth_code.code_challenge = None
        auth_code.ttl = pendulum.now().add(minutes=5).int_timestamp

        mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.get_by_code",
            return_value=auth_code,
        )
        mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.consume_by_id",
            return_value=True,
        )

        with pytest.raises(OAuthException) as excinfo:
            auth_service.exchange_code(
                code="auth_code_123",
                redirect_uri="https://different.com/callback",
            )

        assert excinfo.value.oauth_error == "invalid_grant"

    def test_fail_to_exchange_code_due_to_missing_code_verifier(
        self,
        mocker,
        auth_service: AuthService,
    ):
        auth_code = mocker.MagicMock()
        auth_code.ttl = pendulum.now().add(minutes=5).int_timestamp
        auth_code.redirect_uri = "https://example.com/callback"
        auth_code.code_challenge = "E9Mrozoa2owUG2gw61pfAqgxVrQj5zwJckeqyUmKkqM"
        auth_code.code_challenge_method = "S256"

        mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.get_by_code",
            return_value=auth_code,
        )
        mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.consume_by_id",
            return_value=True,
        )

        with pytest.raises(OAuthException) as excinfo:
            auth_service.exchange_code(
                code="auth_code_123",
                redirect_uri="https://example.com/callback",
                code_verifier=None,
            )

        assert excinfo.value.oauth_error == "invalid_request"

    def test_fail_to_exchange_code_due_to_invalid_pkce_s256(
        self,
        mocker,
        auth_service: AuthService,
    ):
        auth_code = mocker.MagicMock()
        auth_code.ttl = pendulum.now().add(minutes=5).int_timestamp
        auth_code.redirect_uri = "https://example.com/callback"
        auth_code.code_challenge = "E9Mrozoa2owUG2gw61pfAqgxVrQj5zwJckeqyUmKkqM"
        auth_code.code_challenge_method = "S256"

        mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.get_by_code",
            return_value=auth_code,
        )
        mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.consume_by_id",
            return_value=True,
        )

        with pytest.raises(OAuthException) as excinfo:
            auth_service.exchange_code(
                code="auth_code_123",
                redirect_uri="https://example.com/callback",
                code_verifier="invalid_verifier",
            )

        assert excinfo.value.oauth_error == "invalid_grant"

    def test_fail_to_exchange_code_due_to_invalid_pkce_plain(
        self,
        mocker,
        auth_service: AuthService,
    ):
        auth_code = mocker.MagicMock()
        auth_code.ttl = pendulum.now().add(minutes=5).int_timestamp
        auth_code.redirect_uri = "https://example.com/callback"
        auth_code.code_challenge = "expected_challenge"
        auth_code.code_challenge_method = "plain"

        mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.get_by_code",
            return_value=auth_code,
        )
        mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.consume_by_id",
            return_value=True,
        )

        with pytest.raises(OAuthException) as excinfo:
            auth_service.exchange_code(
                code="auth_code_123",
                redirect_uri="https://example.com/callback",
                code_verifier="different_challenge",
            )

        assert excinfo.value.oauth_error == "invalid_grant"

    def test_successfully_exchange_code_with_pkce_s256(
        self,
        mocker,
        auth_service: AuthService,
        user_data: dict,
    ):
        import base64
        import hashlib

        code_verifier = "test_verifier_for_pkce"
        code_challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
            .decode()
            .rstrip("=")
        )

        auth_code = mocker.MagicMock()
        auth_code.id = "auth-code-id-s256"
        auth_code.code = "auth_code_123"
        auth_code.user_id = user_data["id"]
        auth_code.redirect_uri = "https://example.com/callback"
        auth_code.scope = "users:read"
        auth_code.code_challenge = code_challenge
        auth_code.code_challenge_method = "S256"
        auth_code.ttl = pendulum.now().add(minutes=5).int_timestamp

        mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.get_by_code",
            return_value=auth_code,
        )
        mocker.patch.object(UserServiceClient, "get_user_by_id", return_value=user_data)
        mocker.patch("app.services.auth_service.TokenService.create")
        consume_mock = mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.consume_by_id",
            return_value=True,
        )

        jwt_str, refresh_token, exp, scope = auth_service.exchange_code(
            code="auth_code_123",
            redirect_uri="https://example.com/callback",
            code_verifier=code_verifier,
        )

        assert jwt_str is not None
        assert refresh_token is not None
        assert exp == 3600
        assert scope == "users:read"
        consume_mock.assert_called_once_with("auth-code-id-s256")

    def test_successfully_exchange_code_with_pkce_plain(
        self,
        mocker,
        auth_service: AuthService,
        user_data: dict,
    ):
        auth_code = mocker.MagicMock()
        auth_code.id = "auth-code-id-plain"
        auth_code.code = "auth_code_123"
        auth_code.user_id = user_data["id"]
        auth_code.redirect_uri = "https://example.com/callback"
        auth_code.scope = "users:read"
        auth_code.code_challenge = "plain_challenge"
        auth_code.code_challenge_method = "plain"
        auth_code.ttl = pendulum.now().add(minutes=5).int_timestamp

        mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.get_by_code",
            return_value=auth_code,
        )
        mocker.patch.object(UserServiceClient, "get_user_by_id", return_value=user_data)
        mocker.patch("app.services.auth_service.TokenService.create")
        consume_mock = mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.consume_by_id",
            return_value=True,
        )

        jwt_str, refresh_token, exp, scope = auth_service.exchange_code(
            code="auth_code_123",
            redirect_uri="https://example.com/callback",
            code_verifier="plain_challenge",
        )

        assert jwt_str is not None
        assert refresh_token is not None
        assert exp == 3600
        assert scope == "users:read"
        consume_mock.assert_called_once_with("auth-code-id-plain")

    def test_fail_to_exchange_code_due_to_user_not_found(
        self,
        mocker,
        auth_service: AuthService,
    ):
        auth_code = mocker.MagicMock()
        auth_code.id = "auth-code-id-user-not-found"
        auth_code.code = "auth_code_123"
        auth_code.user_id = "nonexistent_user"
        auth_code.redirect_uri = "https://example.com/callback"
        auth_code.code_challenge = None
        auth_code.ttl = pendulum.now().add(minutes=5).int_timestamp

        mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.get_by_code",
            return_value=auth_code,
        )
        mocker.patch.object(UserServiceClient, "get_user_by_id", return_value=None)
        consume_mock = mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.consume_by_id",
            return_value=True,
        )

        with pytest.raises(UserNotFoundException) as excinfo:
            auth_service.exchange_code(
                code="auth_code_123",
                redirect_uri="https://example.com/callback",
            )

        assert "not found" in str(excinfo.value.detail).lower()
        consume_mock.assert_called_once_with("auth-code-id-user-not-found")
