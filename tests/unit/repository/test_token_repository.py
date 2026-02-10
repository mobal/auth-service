import uuid
from typing import Any

import pendulum

from app.models.jwt import JWTToken
from app.repositories.token_repository import TokenRepository


class TestTokenRepository:
    def test_successfully_create_token(
        self, jwt_token: JWTToken, token_repository: TokenRepository, tokens_table
    ):
        jwt_token.jti = str(uuid.uuid4())
        refresh_token = str(uuid.uuid4())
        token = {
            "jti": jwt_token.jti,
            "jwt_token": jwt_token.model_dump(),
            "refresh_token": refresh_token,
            "created_at": pendulum.now().to_iso8601_string(),
            "ttl": jwt_token.exp,
        }
        token_repository.create_token(token)

        response = tokens_table.get_item(
            Key={"jti": token["jti"]},
        )

        assert response["Item"] == token

    def test_successfully_delete_by_id(
        self, jwt_token: JWTToken, token_repository: TokenRepository, tokens_table
    ):
        response = token_repository.delete_by_id(jwt_token.jti)

        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    def test_delete_by_id_returns_none_if_id_not_found(
        self, token_repository: TokenRepository, tokens_table
    ):
        response = token_repository.delete_by_id(str(uuid.uuid4()))

        assert response["Attributes"] == {}

    def test_successfully_get_by_id(
        self,
        jwt_token: JWTToken,
        refresh_token: str,
        token_repository: TokenRepository,
        tokens_table,
    ):
        item = token_repository.get_by_id(jwt_token.jti)

        assert item == (jwt_token, refresh_token)

    def test_get_by_id_returns_none_if_id_not_found(
        self, token_repository: TokenRepository, tokens_table
    ):
        assert token_repository.get_by_id(str(uuid.uuid4())) is None

    def test_successfully_get_by_refresh_token(
        self,
        jwt_token: JWTToken,
        refresh_token: str,
        token: dict[str, Any],
        token_repository: TokenRepository,
        tokens_table,
    ):
        item = token_repository.get_by_refresh_token(refresh_token)

        assert item == token

    def test_get_by_refresh_token_returns_none_if_refresh_token_not_found(
        self, token_repository: TokenRepository, tokens_table
    ):
        assert token_repository.get_by_refresh_token(str(uuid.uuid4())) is None
