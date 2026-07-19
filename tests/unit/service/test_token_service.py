from typing import Any

import pendulum
import pytest

from app.exceptions import TokenNotFoundException
from app.models.jwt import JWTToken, RefreshToken
from app.repositories.token_repository import TokenRepository
from app.services.token_service import TokenService


class TestTokenService:
    def test_successfully_create_token(
        self,
        mocker,
        jwt_token: JWTToken,
        refresh_token: RefreshToken,
        token_repository: TokenRepository,
        token_service: TokenService,
    ):
        mocker.patch.object(TokenRepository, "create_token")

        token_service.create(jwt_token, refresh_token)

        token_repository.create_token.assert_called_once_with(
            {
                "jti": jwt_token.jti,
                "jwt_token": jwt_token.model_dump(),
                "refresh_token": refresh_token.token,
                "created_at": mocker.ANY,
                "expire_at": mocker.ANY,
                "ttl": refresh_token.ttl,
            }
        )

    def test_successfully_create_token_without_refresh_token(
        self,
        mocker,
        jwt_token: JWTToken,
        token_repository: TokenRepository,
        token_service: TokenService,
    ):
        mocker.patch.object(TokenRepository, "create_token")

        token_service.create(jwt_token, None)

        token_repository.create_token.assert_called_once_with(
            {
                "jti": jwt_token.jti,
                "jwt_token": jwt_token.model_dump(),
                "created_at": pendulum.from_timestamp(
                    jwt_token.iat
                ).to_iso8601_string(),
                "expire_at": pendulum.from_timestamp(jwt_token.exp).to_iso8601_string(),
                "ttl": jwt_token.exp,
            }
        )

    def test_successfully_delete_by_id(
        self,
        mocker,
        jwt_token: JWTToken,
        token_repository: TokenRepository,
        token_service: TokenService,
    ):
        mocker.patch.object(
            TokenRepository,
            "delete_by_id",
            return_value={"ResponseMetadata": {"HTTPStatusCode": 200}},
        )

        token_service.delete_by_id(jwt_token.jti)

        token_repository.delete_by_id.assert_called_once_with(jwt_token.jti)

    def test_fail_to_delete_by_id_due_to_token_not_found(
        self,
        mocker,
        jwt_token: JWTToken,
        token_repository: TokenRepository,
        token_service: TokenService,
    ):
        mocker.patch.object(
            TokenRepository,
            "delete_by_id",
            return_value=False,
        )

        with pytest.raises(TokenNotFoundException) as excinfo:
            token_service.delete_by_id(jwt_token.jti)

        assert excinfo.type == TokenNotFoundException
        assert "The requested token was not found" == excinfo.value.detail

        token_repository.delete_by_id.assert_called_once_with(jwt_token.jti)

    def test_successfully_consume_by_id(
        self,
        mocker,
        jwt_token: JWTToken,
        token_repository: TokenRepository,
        token_service: TokenService,
    ):
        mocker.patch.object(TokenRepository, "delete_by_id", return_value=True)

        result = token_service.consume_by_id(jwt_token.jti)

        assert result is True
        token_repository.delete_by_id.assert_called_once_with(jwt_token.jti)

    def test_consume_by_id_returns_false_when_token_not_found(
        self,
        mocker,
        jwt_token: JWTToken,
        token_repository: TokenRepository,
        token_service: TokenService,
    ):
        mocker.patch.object(TokenRepository, "delete_by_id", return_value=False)

        result = token_service.consume_by_id(jwt_token.jti)

        assert result is False
        token_repository.delete_by_id.assert_called_once_with(jwt_token.jti)

    def test_successfully_get_token_by_id(
        self,
        mocker,
        jwt_token: JWTToken,
        token: dict[str, Any],
        token_repository: TokenRepository,
        token_service: TokenService,
    ):
        mocker.patch.object(TokenRepository, "get_by_id", return_value=token)

        result = token_service.get_by_id(jwt_token.jti)

        assert result is not None
        assert result[0].jti == jwt_token.jti
        assert result[0].sub == jwt_token.sub
        assert result[0].scope == jwt_token.scope
        assert result[1] == token.get("refresh_token", "")
        assert result[2] == token["ttl"]
        token_repository.get_by_id.assert_called_once_with(jwt_token.jti)

    def test_successfully_get_token_by_refresh_token(
        self,
        mocker,
        refresh_token: RefreshToken,
        token: dict[str, Any],
        token_repository: TokenRepository,
        token_service: TokenService,
    ):
        mocker.patch.object(
            TokenRepository,
            "get_by_refresh_token",
            return_value=token,
        )

        result = token_service.get_by_refresh_token(refresh_token.token)

        assert result is not None
        assert result[0].jti == token["jti"]
        assert result[0].sub == token["jwt_token"]["sub"]
        assert result[1] == token.get("refresh_token", "")
        assert result[2] == token["ttl"]
        token_repository.get_by_refresh_token.assert_called_once_with(
            refresh_token.token
        )
