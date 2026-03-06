import uuid
from unittest.mock import ANY

import jwt
import pendulum
import pytest as pytest
from argon2 import PasswordHasher
from fastapi import HTTPException, status

from app.exceptions import (
    OAuthException,
    TokenNotFoundException,
    UserNotFoundException,
)
from app.models.jwt import JWTToken, RefreshToken
from app.models.service import ServiceCredential
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.token_service import TokenService
from app.settings import Settings

ALGORITHMS = ["HS256"]


class TestAuthService:
    @pytest.fixture
    def auth_service(self) -> AuthService:
        return AuthService()

    @pytest.fixture
    def password_hasher(self) -> PasswordHasher:
        return PasswordHasher()

    def test_generate_token_with_user_object(
        self, auth_service: AuthService, user: User
    ):
        jwt_token = auth_service._generate_token(sub=user.id, user=user, exp=3600)

        assert jwt_token.sub == user.id
        assert jwt_token.user is not None
        assert "password" not in jwt_token.user
        assert "created_at" not in jwt_token.user
        assert "deleted_at" not in jwt_token.user
        assert "updated_at" not in jwt_token.user
        assert jwt_token.user["id"] == user.id
        assert jwt_token.user["email"] == user.email

    def test_successfully_login(
        self,
        mocker,
        auth_service: AuthService,
        password: str,
        settings: Settings,
        token_service: TokenService,
        user: User,
        user_repository: UserRepository,
    ):
        mocker.patch.object(UserRepository, "get_by_email", return_value=user)
        mocker.patch.object(TokenService, "create")

        jwt_token, _, _, _ = auth_service.login(user.email, password)
        decoded_jwt_token = JWTToken(
            **jwt.decode(jwt_token, settings.jwt_secret, ALGORITHMS)
        )

        assert user.id == decoded_jwt_token.sub
        assert (
            pendulum.from_timestamp(decoded_jwt_token.exp)
            - pendulum.from_timestamp(decoded_jwt_token.iat)
        ).in_words() == "1 hour"
        user_repository.get_by_email.assert_called_once_with(user.email)
        token_service.create.assert_called_once_with(decoded_jwt_token, ANY)

    def test_fail_to_login_due_user_not_found_by_email(
        self,
        mocker,
        auth_service: AuthService,
        password: str,
        user: User,
        user_repository: UserRepository,
    ):
        error_message = "The requested user was not found"
        mocker.patch.object(UserRepository, "get_by_email", return_value=None)

        with pytest.raises(UserNotFoundException) as excinfo:
            auth_service.login(user.email, password)

        assert status.HTTP_404_NOT_FOUND == excinfo.value.status_code
        assert error_message == excinfo.value.detail
        user_repository.get_by_email.assert_called_once_with(user.email)

    def test_fail_to_login_due_password_does_not_match(
        self,
        mocker,
        auth_service: AuthService,
        password_hasher: PasswordHasher,
        user: User,
        user_repository: UserRepository,
    ):
        mocker.patch.object(UserRepository, "get_by_email", return_value=user)

        with pytest.raises(HTTPException) as excinfo:
            auth_service.login(user.email, password_hasher.hash("doest_not_match"))

        assert status.HTTP_401_UNAUTHORIZED == excinfo.value.status_code
        assert "Unauthorized" == excinfo.value.detail
        user_repository.get_by_email.assert_called_once_with(user.email)

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
                "user": {"id": "user-1", "email": "root@squarelabs.hu"},
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
                "user": {"id": "user-1", "email": "root@squarelabs.hu"},
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
            "app.services.auth_service.ServiceRepository.get_by_id",
            return_value=service_credential,
        )
        mocker.patch.object(TokenService, "create")

        token, expires_in, scope = auth_service.client_credentials(
            service_credential.id, password, None
        )
        decoded = JWTToken(
            **jwt.decode(token, settings.jwt_secret, algorithms=ALGORITHMS)
        )

        assert decoded.sub == service_credential.id
        assert decoded.scope == scope
        assert expires_in == settings.jwt_token_lifetime
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
            "app.services.auth_service.ServiceRepository.get_by_id",
            return_value=service_credential,
        )
        mocker.patch.object(TokenService, "create")

        _, _, scope = auth_service.client_credentials(
            service_credential.id, password, "users:read"
        )

        assert scope == "users:read"
        auth_service._token_service.create.assert_called_once()

    def test_fail_to_client_credentials_due_to_missing_service(
        self, mocker, auth_service: AuthService
    ):
        mocker.patch(
            "app.services.auth_service.ServiceRepository.get_by_id",
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
            "app.services.auth_service.ServiceRepository.get_by_id",
            return_value=service_credential,
        )

        with pytest.raises(OAuthException) as excinfo:
            auth_service.client_credentials(service_credential.id, "wrong-secret", None)

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
            "app.services.auth_service.ServiceRepository.get_by_id",
            return_value=service_credential,
        )

        with pytest.raises(OAuthException) as excinfo:
            auth_service.client_credentials(
                service_credential.id, password, "tokens:revoke"
            )

        assert excinfo.value.oauth_error == "invalid_scope"

    def test_successfully_authorize_with_user(
        self,
        mocker,
        auth_service: AuthService,
        user: User,
    ):
        mocker.patch(
            "app.services.auth_service.UserRepository.get_by_id",
            return_value=user,
        )
        create_mock = mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.create",
            return_value="test_code_123",
        )

        code = auth_service.authorize(
            user_id=user.id,
            client_id="client_123",
            redirect_uri="https://example.com/callback",
            requested_scope="users:read",
        )

        assert code == "test_code_123"
        create_mock.assert_called_once()
        call_kwargs = create_mock.call_args[1]
        assert call_kwargs["client_id"] == "client_123"
        assert call_kwargs["user_id"] == user.id
        assert call_kwargs["redirect_uri"] == "https://example.com/callback"
        assert call_kwargs["scope"] == "users:read"
        assert call_kwargs["code_challenge"] is None
        assert call_kwargs["code_challenge_method"] is None

    def test_successfully_authorize_with_pkce_s256(
        self,
        mocker,
        auth_service: AuthService,
        user: User,
    ):
        mocker.patch(
            "app.services.auth_service.UserRepository.get_by_id",
            return_value=user,
        )
        create_mock = mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.create",
            return_value="test_code_pkce",
        )

        code = auth_service.authorize(
            user_id=user.id,
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
        user: User,
    ):
        mocker.patch(
            "app.services.auth_service.UserRepository.get_by_id",
            return_value=user,
        )
        create_mock = mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.create",
            return_value="test_code_plain",
        )

        code = auth_service.authorize(
            user_id=user.id,
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
        mocker.patch(
            "app.services.auth_service.UserRepository.get_by_id",
            return_value=None,
        )

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
        user: User,
    ):
        import pendulum

        auth_code_data = {
            "code": "auth_code_123",
            "client_id": "client_123",
            "user_id": user.id,
            "redirect_uri": "https://example.com/callback",
            "scope": "users:read",
            "code_challenge": None,
            "code_challenge_method": None,
            "ttl": pendulum.now().add(minutes=5).int_timestamp,
        }
        auth_code = mocker.MagicMock()
        auth_code.code = auth_code_data["code"]
        auth_code.user_id = auth_code_data["user_id"]
        auth_code.redirect_uri = auth_code_data["redirect_uri"]
        auth_code.scope = auth_code_data["scope"]
        auth_code.code_challenge = None
        auth_code.ttl = auth_code_data["ttl"]

        mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.get_by_code",
            return_value=auth_code,
        )
        mocker.patch(
            "app.services.auth_service.UserRepository.get_by_id",
            return_value=user,
        )
        mocker.patch(
            "app.services.auth_service.TokenService.create",
        )
        delete_mock = mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.delete_by_code"
        )

        jwt_str, refresh_token, exp, scope = auth_service.exchange_code(
            code="auth_code_123",
            redirect_uri="https://example.com/callback",
        )

        assert jwt_str is not None
        assert refresh_token is not None
        assert exp == 3600
        assert scope == "users:read"
        delete_mock.assert_called_once_with("auth_code_123")

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
        import pendulum

        auth_code = mocker.MagicMock()
        auth_code.ttl = pendulum.now().subtract(minutes=5).int_timestamp
        auth_code.redirect_uri = "https://example.com/callback"

        mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.get_by_code",
            return_value=auth_code,
        )
        delete_mock = mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.delete_by_code"
        )

        with pytest.raises(OAuthException) as excinfo:
            auth_service.exchange_code(
                code="expired_code",
                redirect_uri="https://example.com/callback",
            )

        assert excinfo.value.oauth_error == "invalid_grant"
        delete_mock.assert_called_once_with("expired_code")

    def test_fail_to_exchange_code_due_to_redirect_uri_mismatch(
        self,
        mocker,
        auth_service: AuthService,
    ):
        import pendulum

        auth_code = mocker.MagicMock()
        auth_code.code = "auth_code_123"
        auth_code.ttl = pendulum.now().add(minutes=5).int_timestamp
        auth_code.redirect_uri = "https://example.com/callback"
        auth_code.code_challenge = None

        mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.get_by_code",
            return_value=auth_code,
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
        import pendulum

        auth_code = mocker.MagicMock()
        auth_code.code = "auth_code_123"
        auth_code.ttl = pendulum.now().add(minutes=5).int_timestamp
        auth_code.redirect_uri = "https://example.com/callback"
        auth_code.code_challenge = "E9Mrozoa2owUG2gw61pfAqgxVrQj5zwJckeqyUmKkqM"
        auth_code.code_challenge_method = "S256"

        mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.get_by_code",
            return_value=auth_code,
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
        import pendulum

        auth_code = mocker.MagicMock()
        auth_code.ttl = pendulum.now().add(minutes=5).int_timestamp
        auth_code.redirect_uri = "https://example.com/callback"
        auth_code.code_challenge = "E9Mrozoa2owUG2gw61pfAqgxVrQj5zwJckeqyUmKkqM"
        auth_code.code_challenge_method = "S256"

        mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.get_by_code",
            return_value=auth_code,
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
        import pendulum

        auth_code = mocker.MagicMock()
        auth_code.ttl = pendulum.now().add(minutes=5).int_timestamp
        auth_code.redirect_uri = "https://example.com/callback"
        auth_code.code_challenge = "expected_challenge"
        auth_code.code_challenge_method = "plain"

        mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.get_by_code",
            return_value=auth_code,
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
        user: User,
    ):
        import base64
        import hashlib

        import pendulum

        code_verifier = "test_verifier_for_pkce"
        code_challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
            .decode()
            .rstrip("=")
        )

        auth_code = mocker.MagicMock()
        auth_code.code = "auth_code_123"
        auth_code.user_id = user.id
        auth_code.redirect_uri = "https://example.com/callback"
        auth_code.scope = "users:read"
        auth_code.code_challenge = code_challenge
        auth_code.code_challenge_method = "S256"
        auth_code.ttl = pendulum.now().add(minutes=5).int_timestamp

        mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.get_by_code",
            return_value=auth_code,
        )
        mocker.patch(
            "app.services.auth_service.UserRepository.get_by_id",
            return_value=user,
        )
        mocker.patch(
            "app.services.auth_service.TokenService.create",
        )
        delete_mock = mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.delete_by_code"
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
        delete_mock.assert_called_once_with("auth_code_123")

    def test_successfully_exchange_code_with_pkce_plain(
        self,
        mocker,
        auth_service: AuthService,
        user: User,
    ):
        import pendulum

        auth_code = mocker.MagicMock()
        auth_code.code = "auth_code_123"
        auth_code.user_id = user.id
        auth_code.redirect_uri = "https://example.com/callback"
        auth_code.scope = "users:read"
        auth_code.code_challenge = "plain_challenge"
        auth_code.code_challenge_method = "plain"
        auth_code.ttl = pendulum.now().add(minutes=5).int_timestamp

        mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.get_by_code",
            return_value=auth_code,
        )
        mocker.patch(
            "app.services.auth_service.UserRepository.get_by_id",
            return_value=user,
        )
        mocker.patch(
            "app.services.auth_service.TokenService.create",
        )
        delete_mock = mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.delete_by_code"
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
        delete_mock.assert_called_once()

    def test_fail_to_exchange_code_due_to_user_not_found(
        self,
        mocker,
        auth_service: AuthService,
    ):
        import pendulum

        auth_code = mocker.MagicMock()
        auth_code.code = "auth_code_123"
        auth_code.user_id = "nonexistent_user"
        auth_code.redirect_uri = "https://example.com/callback"
        auth_code.code_challenge = None
        auth_code.ttl = pendulum.now().add(minutes=5).int_timestamp

        mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.get_by_code",
            return_value=auth_code,
        )
        mocker.patch(
            "app.services.auth_service.UserRepository.get_by_id",
            return_value=None,
        )
        delete_mock = mocker.patch(
            "app.services.auth_service.AuthorizationCodeRepository.delete_by_code"
        )

        with pytest.raises(UserNotFoundException) as excinfo:
            auth_service.exchange_code(
                code="auth_code_123",
                redirect_uri="https://example.com/callback",
            )

        assert "not found" in str(excinfo.value.detail).lower()
        delete_mock.assert_called_once_with("auth_code_123")
