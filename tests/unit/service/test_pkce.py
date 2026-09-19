import time
from unittest.mock import MagicMock

import pytest
from argon2 import PasswordHasher

from app.exceptions import OAuthException
from app.models.authorization_code import AuthorizationCode
from app.repositories.authorization_code_repository import AuthorizationCodeRepository
from app.services.auth_service import AuthService


class TestAuthServicePKCE:
    @pytest.fixture
    def auth_service(self) -> tuple[AuthService, MagicMock]:
        repository = MagicMock(spec=AuthorizationCodeRepository)
        service = AuthService(
            password_hasher=MagicMock(spec=PasswordHasher),
            authorization_code_repository=repository,
            service_repository=MagicMock(),
            token_service=MagicMock(),
            user_service_client=MagicMock(),
            role_scope_repository=MagicMock(),
        )
        return service, repository

    def test_validate_s256_rejects_wrong_verifier(
        self, auth_service: tuple[AuthService, MagicMock]
    ):
        service, _ = auth_service
        auth_code = AuthorizationCode(
            id="code-id",
            code="code",
            client_id="client",
            user_id="user",
            redirect_uri="https://client.example/callback",
            code_challenge="E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
            code_challenge_method="S256",
            ttl=int(time.time()) + 600,
        )

        with pytest.raises(OAuthException) as exc_info:
            service._validate_pkce(
                auth_code, "wrong-verifier-that-is-long-enough-for-pkce-x"
            )

        assert exc_info.value.oauth_error == "invalid_grant"

    def test_exchange_consumes_code_before_validating_pkce(
        self, auth_service: tuple[AuthService, MagicMock]
    ):
        service, repository = auth_service
        repository.get_by_code.return_value = AuthorizationCode(
            id="code-id",
            code="code",
            client_id="client",
            user_id="user",
            redirect_uri="https://client.example/callback",
            code_challenge="E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
            code_challenge_method="S256",
            ttl=int(time.time()) + 600,
        )
        repository.consume_by_id.return_value = True

        with pytest.raises(OAuthException) as exc_info:
            service.exchange_code(
                "code",
                "https://client.example/callback",
                "wrong-verifier-that-is-long-enough-for-pkce-x",
                "client",
            )

        assert exc_info.value.oauth_error == "invalid_grant"
        repository.consume_by_id.assert_called_once_with("code-id")
