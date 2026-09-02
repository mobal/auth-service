import time
import uuid

import pytest
from botocore.exceptions import ClientError

from app.models.authorization_code import AuthorizationCode
from app.repositories.authorization_code_repository import (
    AuthorizationCodeRepository,
)


class TestAuthorizationCodeRepository:
    @pytest.fixture
    def repository(self, authorization_codes_table) -> AuthorizationCodeRepository:
        return AuthorizationCodeRepository()

    def test_successfully_create_authorization_code(
        self, repository: AuthorizationCodeRepository
    ):
        client_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        redirect_uri = "https://example.com/callback"
        scope = "users:read"

        code = repository.create(
            client_id=client_id,
            user_id=user_id,
            redirect_uri=redirect_uri,
            scope=scope,
        )

        assert code is not None
        assert isinstance(code, str)
        assert len(code) > 0

    def test_successfully_create_authorization_code_with_pkce_s256(
        self, repository: AuthorizationCodeRepository
    ):
        client_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        redirect_uri = "https://example.com/callback"
        scope = "users:read"
        code_challenge = "E9Mrozoa2owUG2gw61pfAqgxVrQj5zwJckeqyUmKkqM"
        code_challenge_method = "S256"

        code = repository.create(
            client_id=client_id,
            user_id=user_id,
            redirect_uri=redirect_uri,
            scope=scope,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
        )

        assert code is not None

    def test_successfully_create_authorization_code_with_pkce_plain(
        self, repository: AuthorizationCodeRepository
    ):
        client_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        redirect_uri = "https://example.com/callback"
        code_challenge = "plain_challenge"
        code_challenge_method = "plain"

        code = repository.create(
            client_id=client_id,
            user_id=user_id,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
        )

        assert code is not None

    def test_successfully_create_authorization_code_without_scope(
        self, repository: AuthorizationCodeRepository
    ):
        client_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        redirect_uri = "https://example.com/callback"

        code = repository.create(
            client_id=client_id,
            user_id=user_id,
            redirect_uri=redirect_uri,
        )

        assert code is not None

    def test_successfully_get_authorization_code_by_code(
        self, repository: AuthorizationCodeRepository
    ):
        client_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        redirect_uri = "https://example.com/callback"
        scope = "users:read"

        code = repository.create(
            client_id=client_id,
            user_id=user_id,
            redirect_uri=redirect_uri,
            scope=scope,
        )

        auth_code = repository.get_by_code(code)

        assert auth_code is not None
        assert isinstance(auth_code, AuthorizationCode)
        assert auth_code.code == code
        assert auth_code.client_id == client_id
        assert auth_code.user_id == user_id
        assert auth_code.redirect_uri == redirect_uri
        assert auth_code.scope == scope

    def test_successfully_get_authorization_code_with_pkce(
        self, repository: AuthorizationCodeRepository
    ):
        client_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        redirect_uri = "https://example.com/callback"
        code_challenge = "E9Mrozoa2owUG2gw61pfAqgxVrQj5zwJckeqyUmKkqM"
        code_challenge_method = "S256"

        code = repository.create(
            client_id=client_id,
            user_id=user_id,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
        )

        auth_code = repository.get_by_code(code)

        assert auth_code is not None
        assert auth_code.code_challenge == code_challenge
        assert auth_code.code_challenge_method == code_challenge_method

    def test_get_authorization_code_returns_none_for_missing_code(
        self, repository: AuthorizationCodeRepository
    ):
        auth_code = repository.get_by_code("nonexistent_code_xyz")

        assert auth_code is None

    def test_successfully_delete_authorization_code(
        self, repository: AuthorizationCodeRepository
    ):
        client_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        redirect_uri = "https://example.com/callback"

        code = repository.create(
            client_id=client_id,
            user_id=user_id,
            redirect_uri=redirect_uri,
        )

        auth_code = repository.get_by_code(code)
        assert auth_code is not None

        repository.delete_by_id(auth_code.id)

        auth_code = repository.get_by_code(code)
        assert auth_code is None

    def test_successfully_delete_authorization_code_one_time_use(
        self, repository: AuthorizationCodeRepository
    ):
        client_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        redirect_uri = "https://example.com/callback"
        code_challenge = "E9Mrozoa2owUG2gw61pfAqgxVrQj5zwJckeqyUmKkqM"

        code = repository.create(
            client_id=client_id,
            user_id=user_id,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )

        auth_code = repository.get_by_code(code)
        assert auth_code is not None
        assert auth_code.code_challenge == code_challenge

        repository.delete_by_id(auth_code.id)

        auth_code = repository.get_by_code(code)
        assert auth_code is None

    def test_successfully_consume_authorization_code(
        self, repository: AuthorizationCodeRepository
    ):
        client_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        redirect_uri = "https://example.com/callback"

        code = repository.create(
            client_id=client_id,
            user_id=user_id,
            redirect_uri=redirect_uri,
        )

        auth_code = repository.get_by_code(code)
        assert auth_code is not None

        assert repository.consume_by_id(auth_code.id) is True
        assert repository.consume_by_id(auth_code.id) is False

    def test_fail_to_consume_authorization_code_twice(
        self, repository: AuthorizationCodeRepository
    ):
        client_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        redirect_uri = "https://example.com/callback"

        code = repository.create(
            client_id=client_id,
            user_id=user_id,
            redirect_uri=redirect_uri,
        )

        auth_code = repository.get_by_code(code)
        assert auth_code is not None

        assert repository.consume_by_id(auth_code.id) is True
        assert repository.consume_by_id(auth_code.id) is False

    def test_fail_to_consume_authorization_code_nonexistent_id(
        self, repository: AuthorizationCodeRepository
    ):
        assert repository.consume_by_id("nonexistent-id") is False

    def test_authorization_code_has_correct_ttl(
        self, repository: AuthorizationCodeRepository
    ):
        client_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        redirect_uri = "https://example.com/callback"

        before_create = int(time.time())
        code = repository.create(
            client_id=client_id,
            user_id=user_id,
            redirect_uri=redirect_uri,
        )
        after_create = int(time.time())

        auth_code = repository.get_by_code(code)
        assert auth_code is not None
        assert auth_code.ttl is not None

        expected_ttl = before_create + 600
        assert expected_ttl - 60 <= auth_code.ttl <= after_create + 600 + 60

    def test_create_generates_unique_codes(
        self, repository: AuthorizationCodeRepository
    ):
        client_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        redirect_uri = "https://example.com/callback"

        code1 = repository.create(
            client_id=client_id,
            user_id=user_id,
            redirect_uri=redirect_uri,
        )

        code2 = repository.create(
            client_id=client_id,
            user_id=user_id,
            redirect_uri=redirect_uri,
        )

        assert code1 != code2
        assert repository.get_by_code(code1) is not None
        assert repository.get_by_code(code2) is not None

    def test_create_raises_client_error_on_throttling(
        self, mocker, repository: AuthorizationCodeRepository
    ):
        error_response = {
            "Error": {
                "Code": "ProvisionedThroughputExceededException",
                "Message": "Rate exceeded",
            }
        }
        mocker.patch.object(
            repository._table,
            "put_item",
            side_effect=ClientError(error_response, "PutItem"),
        )
        with pytest.raises(ClientError):
            repository.create(
                client_id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                redirect_uri="https://example.com/callback",
            )

    def test_delete_by_id_raises_client_error_on_throttling(
        self, mocker, repository: AuthorizationCodeRepository
    ):
        error_response = {
            "Error": {
                "Code": "ProvisionedThroughputExceededException",
                "Message": "Rate exceeded",
            }
        }
        mocker.patch.object(
            repository._table,
            "delete_item",
            side_effect=ClientError(error_response, "DeleteItem"),
        )
        with pytest.raises(ClientError):
            repository.delete_by_id("nonexistent-id")

    def test_get_by_code_raises_client_error(
        self, mocker, repository: AuthorizationCodeRepository
    ):
        error_response = {
            "Error": {
                "Code": "InternalServerError",
                "Message": "Internal error",
            }
        }
        mocker.patch.object(
            repository._table,
            "query",
            side_effect=ClientError(error_response, "Query"),
        )
        with pytest.raises(ClientError):
            repository.get_by_code("some-code")

    def test_consume_by_id_raises_unexpected_client_error(
        self, mocker, repository: AuthorizationCodeRepository
    ):
        code = repository.create(
            client_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            redirect_uri="https://example.com/callback",
        )
        auth_code = repository.get_by_code(code)
        assert auth_code is not None

        error_response = {
            "Error": {
                "Code": "InternalServerError",
                "Message": "Internal error",
            }
        }
        mocker.patch.object(
            repository._table,
            "update_item",
            side_effect=ClientError(error_response, "UpdateItem"),
        )
        with pytest.raises(ClientError):
            repository.consume_by_id(auth_code.id)
