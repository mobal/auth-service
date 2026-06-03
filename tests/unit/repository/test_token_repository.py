import uuid
from typing import Any

import pendulum
import pytest
from botocore.exceptions import ClientError

from app.models.jwt import JWTToken, RefreshToken
from app.repositories.token_repository import TokenRepository


class TestTokenRepository:
    def test_successfully_create_token(
        self,
        jwt_token: JWTToken,
        refresh_token: RefreshToken,
        token_repository: TokenRepository,
        tokens_table,
    ):
        jwt_token.jti = str(uuid.uuid4())
        token = {
            "jti": jwt_token.jti,
            "jwt_token": jwt_token.model_dump(),
            "refresh_token": refresh_token.token,
            "created_at": pendulum.now().to_iso8601_string(),
            "expire_at": pendulum.from_timestamp(refresh_token.ttl).to_iso8601_string(),
            "ttl": refresh_token.ttl,
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

        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    def test_successfully_consume_by_id(
        self, jwt_token: JWTToken, token_repository: TokenRepository, tokens_table
    ):
        assert token_repository.consume_by_id(jwt_token.jti) is True

        item = token_repository.get_by_id(jwt_token.jti)
        assert item is None

    def test_consume_by_id_returns_false_if_already_consumed(
        self, jwt_token: JWTToken, token_repository: TokenRepository, tokens_table
    ):
        assert token_repository.consume_by_id(jwt_token.jti) is True
        assert token_repository.consume_by_id(jwt_token.jti) is False

    def test_consume_by_id_returns_false_if_not_found(
        self, token_repository: TokenRepository, tokens_table
    ):
        assert token_repository.consume_by_id(str(uuid.uuid4())) is False

    def test_successfully_get_by_id(
        self,
        jwt_token: JWTToken,
        refresh_token: RefreshToken,
        token: dict[str, Any],
        token_repository: TokenRepository,
        tokens_table,
    ):
        item = token_repository.get_by_id(jwt_token.jti)

        assert item == token

    def test_get_by_id_returns_none_if_id_not_found(
        self, token_repository: TokenRepository, tokens_table
    ):
        assert token_repository.get_by_id(str(uuid.uuid4())) is None

    def test_successfully_get_by_refresh_token(
        self,
        refresh_token: RefreshToken,
        token: dict[str, Any],
        token_repository: TokenRepository,
        tokens_table,
    ):
        item = token_repository.get_by_refresh_token(refresh_token.token)

        assert item == token

    def test_get_by_refresh_token_returns_none_if_refresh_token_not_found(
        self, token_repository: TokenRepository, tokens_table
    ):
        assert token_repository.get_by_refresh_token(str(uuid.uuid4())) is None

    def test_create_token_raises_client_error_on_throttling(
        self,
        mocker,
        jwt_token: JWTToken,
        refresh_token: RefreshToken,
        token_repository: TokenRepository,
    ):
        error_response = {
            "Error": {
                "Code": "ProvisionedThroughputExceededException",
                "Message": "Rate exceeded",
            }
        }
        mocker.patch.object(
            token_repository._table,
            "put_item",
            side_effect=ClientError(error_response, "PutItem"),
        )
        token = {
            "jti": str(uuid.uuid4()),
            "jwt_token": jwt_token.model_dump(),
            "refresh_token": refresh_token.token,
            "created_at": pendulum.now().to_iso8601_string(),
            "expire_at": pendulum.from_timestamp(refresh_token.ttl).to_iso8601_string(),
            "ttl": refresh_token.ttl,
        }
        with pytest.raises(ClientError):
            token_repository.create_token(token)

    def test_delete_by_id_raises_client_error(
        self,
        mocker,
        jwt_token: JWTToken,
        token_repository: TokenRepository,
    ):
        error_response = {
            "Error": {
                "Code": "InternalServerError",
                "Message": "Internal error",
            }
        }
        mocker.patch.object(
            token_repository._table,
            "delete_item",
            side_effect=ClientError(error_response, "DeleteItem"),
        )
        with pytest.raises(ClientError):
            token_repository.delete_by_id(jwt_token.jti)

    def test_get_by_id_raises_client_error(
        self,
        mocker,
        token_repository: TokenRepository,
    ):
        error_response = {
            "Error": {
                "Code": "InternalServerError",
                "Message": "Internal error",
            }
        }
        mocker.patch.object(
            token_repository._table,
            "get_item",
            side_effect=ClientError(error_response, "GetItem"),
        )
        with pytest.raises(ClientError):
            token_repository.get_by_id(str(uuid.uuid4()))

    def test_get_by_refresh_token_raises_client_error(
        self,
        mocker,
        token_repository: TokenRepository,
    ):
        error_response = {
            "Error": {
                "Code": "InternalServerError",
                "Message": "Internal error",
            }
        }
        mocker.patch.object(
            token_repository._table,
            "query",
            side_effect=ClientError(error_response, "Query"),
        )
        with pytest.raises(ClientError):
            token_repository.get_by_refresh_token(str(uuid.uuid4()))
