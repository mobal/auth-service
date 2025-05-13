from typing import Any

import pytest

from app.exceptions import TokenNotFoundException
from app.models import JWTToken
from app.repositories import TokenRepository
from app.services import TokenService


class TestTokenService:
    def test_successfully_create_token(
        self,
        mocker,
        jwt_token: JWTToken,
        refresh_token: str,
        token: dict[str, Any],
        token_repository: TokenRepository,
        token_service: TokenService,
    ):
        mocker.patch.object(TokenRepository, "create_token")

        token_service.create(jwt_token, refresh_token)

        token_repository.create_token.assert_called_once_with(token)

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
            return_value={"ResponseMetadata": {"HTTPStatusCode": 404}},
        )

        with pytest.raises(TokenNotFoundException) as excinfo:
            token_service.delete_by_id(jwt_token.jti)

        assert TokenNotFoundException.__name__ == excinfo.typename
        assert "The requested token was not found" == excinfo.value.detail

        token_repository.delete_by_id.assert_called_once_with(jwt_token.jti)

    def test_successfully_get_token_by_id(
        self,
        mocker,
        jwt_token: JWTToken,
        token_repository: TokenRepository,
        token_service: TokenService,
    ):
        mocker.patch.object(
            TokenRepository, "get_by_id", return_value=(jwt_token, "refresh_token")
        )

        token_service.get_by_id(jwt_token.jti)

        token_repository.get_by_id.assert_called_once_with(jwt_token.jti)

    def test_successfully_get_token_by_refresh_token(
        self,
        mocker,
        refresh_token: str,
        token: dict[str, Any],
        token_repository: TokenRepository,
        token_service: TokenService,
    ):
        mocker.patch.object(
            TokenRepository,
            "get_by_refresh_token",
            return_value=token,
        )

        token_service.get_by_refresh_token(refresh_token)

        token_repository.get_by_refresh_token.assert_called_once_with(refresh_token)
