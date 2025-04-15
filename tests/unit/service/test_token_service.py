from sys import exc_info
from typing import Any
from unittest.mock import ANY

import pytest

from app.exceptions import TokenNotFoundException
from app.models import JWTToken
from app.repositories import TokenRepository
from app.services import TokenService


@pytest.mark.asyncio
class TestTokenService:
    @pytest.fixture
    def token(self, jwt_token: JWTToken, refresh_token: str) -> dict[str, Any]:
        return {
            "jti": jwt_token.jti,
            "jwt_token": jwt_token.model_dump(),
            "refresh_token": refresh_token,
            "created_at": ANY,
            "ttl": jwt_token.exp,
        }

    @pytest.fixture
    def token_service(self) -> TokenService:
        return TokenService()

    async def test_successfully_create_token(
        self,
        mocker,
        jwt_token: JWTToken,
        refresh_token: str,
        token: dict[str, Any],
        token_repository: TokenRepository,
        token_service: TokenService,
    ):
        mocker.patch.object(TokenRepository, "create_token")

        await token_service.create(jwt_token, refresh_token)

        token_repository.create_token.assert_called_once_with(token)

    async def test_successfully_delete_by_id(
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

        await token_service.delete_by_id(jwt_token.jti)

        token_repository.delete_by_id.assert_called_once_with(jwt_token.jti)

    async def test_fail_to_delete_by_id_due_to_token_not_found(
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

        with pytest.raises(TokenNotFoundException) as exc_info:
            await token_service.delete_by_id(jwt_token.jti)

        assert TokenNotFoundException.__name__ == exc_info.typename
        assert "The requested token was not found" == exc_info.value.detail

        token_repository.delete_by_id.assert_called_once_with(jwt_token.jti)

    async def test_successfully_get_token_by_id(
        self,
        mocker,
        jwt_token: JWTToken,
        token_repository: TokenRepository,
        token_service: TokenService,
    ):
        mocker.patch.object(
            TokenRepository, "get_by_id", return_value=(jwt_token, "refresh_token")
        )

        await token_service.get_by_id(jwt_token.jti)

        token_repository.get_by_id.assert_called_once_with(jwt_token.jti)

    async def test_successfully_get_token_by_refresh_token(
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

        await token_service.get_by_refresh_token(refresh_token)

        token_repository.get_by_refresh_token.assert_called_once_with(refresh_token)
