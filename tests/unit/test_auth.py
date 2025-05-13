from unittest.mock import Mock

import jwt
import pytest
from fastapi import HTTPException, status
from starlette.requests import Request

from app.jwt_bearer import JWTBearer
from app.services import JWTToken, TokenService
from app.settings import Settings

NOT_AUTHENTICATED = "Not authenticated"


class TestJWTAuth:
    @pytest.fixture
    def empty_request(self) -> Mock:
        request = Mock()
        request.headers = {}
        request.query_params = dict()
        return request

    @pytest.fixture
    def jwt_auth(self) -> JWTBearer:
        return JWTBearer()

    @pytest.fixture
    def valid_request(
        self, empty_request: Mock, jwt_token: JWTToken, settings: Settings
    ) -> Mock:
        empty_request.headers = {
            "Authorization": f"Bearer {jwt.encode(jwt_token.model_dump(), settings.jwt_secret)}"
        }
        return empty_request

    def test_fail_to_authorize_request_due_to_authorization_header_is_empty(
        self, empty_request: Mock, jwt_bearer: JWTBearer
    ):
        empty_request.headers = {"Authorization": ""}

        with pytest.raises(HTTPException) as excinfo:
            jwt_bearer(empty_request)

        assert NOT_AUTHENTICATED == excinfo.value.detail
        assert status.HTTP_403_FORBIDDEN == excinfo.value.status_code

    def test_fail_to_authorize_request_due_to_authorization_header_is_missing(
        self, empty_request: Mock, jwt_bearer: JWTBearer
    ):
        with pytest.raises(HTTPException) as excinfo:
            jwt_bearer(empty_request)

        assert NOT_AUTHENTICATED == excinfo.value.detail
        assert status.HTTP_403_FORBIDDEN == excinfo.value.status_code

    def test_fail_to_authorize_request_due_to_bearer_token_is_invalid(
        self, empty_request: Mock, jwt_bearer: JWTBearer
    ):
        empty_request.headers = {"Authorization": "Bearer asdf"}

        with pytest.raises(HTTPException) as excinfo:
            jwt_bearer(empty_request)

        assert NOT_AUTHENTICATED == excinfo.value.detail
        assert status.HTTP_403_FORBIDDEN == excinfo.value.status_code

    def test_fail_to_authorize_request_due_to_bearer_token_is_invalid_with_auto_error_false(
        self, empty_request: Mock
    ):
        empty_request.headers = {"Authorization": "Bearer asdf"}

        jwt_bearer = JWTBearer(auto_error=False)

        result = jwt_bearer(empty_request)

        assert result is None

    def test_fail_to_authorize_request_due_to_bearer_token_is_missing(
        self, empty_request: Mock, jwt_bearer: JWTBearer
    ):
        empty_request.headers = {"Authorization": "Bearer "}

        with pytest.raises(HTTPException) as excinfo:
            jwt_bearer(empty_request)

        assert NOT_AUTHENTICATED == excinfo.value.detail
        assert status.HTTP_403_FORBIDDEN == excinfo.value.status_code

    def test_fail_to_authorize_request_due_to_bearer_token_is_missing_with_auto_error_false(
        self, empty_request: Mock, jwt_bearer: JWTBearer
    ):
        empty_request.headers = {"Authorization": "Bearer "}
        jwt_bearer = JWTBearer(auto_error=False)

        assert jwt_bearer(empty_request) is None

    def test_fail_to_authorize_request_due_to_blacklisted_token(
        self,
        mocker,
        jwt_bearer: JWTBearer,
        jwt_token: JWTToken,
        token_service: TokenService,
        valid_request: Request,
    ):
        mocker.patch.object(TokenService, "get_by_id", return_value=None)

        with pytest.raises(HTTPException) as excinfo:
            jwt_bearer(valid_request)

        assert NOT_AUTHENTICATED == excinfo.value.detail
        assert status.HTTP_403_FORBIDDEN == excinfo.value.status_code
        token_service.get_by_id.assert_called_once_with(jwt_token.jti)

    def test_fail_to_authorize_request_due_to_invalid_scheme(
        self,
        empty_request,
        jwt_bearer: JWTBearer,
        jwt_token: JWTToken,
        settings: Settings,
    ):
        empty_request.headers = {
            "Authorization": f"Bear {jwt.encode(jwt_token.model_dump(), settings.jwt_secret)}"
        }

        with pytest.raises(HTTPException) as excinfo:
            jwt_bearer(empty_request)

        assert excinfo.typename == HTTPException.__name__
        assert excinfo.value.status_code == status.HTTP_403_FORBIDDEN
        assert excinfo.value.detail == "Invalid authentication credentials"

    def test_fail_to_authorize_request_due_to_invalid_scheme_with_auto_error_false(
        self,
        empty_request,
        jwt_token: JWTToken,
        settings: Settings,
    ):
        empty_request.headers = {
            "Authorization": f"Bear {jwt.encode(jwt_token.model_dump(), settings.jwt_secret)}"
        }
        jwt_bearer = JWTBearer(auto_error=False)

        assert jwt_bearer(empty_request) is None

    def test_fail_to_authorize_request_due_to_missing_credentials(
        self, empty_request: Mock
    ):
        jwt_bearer = JWTBearer()

        with pytest.raises(HTTPException) as excinfo:
            jwt_bearer(empty_request)

        assert status.HTTP_403_FORBIDDEN == excinfo.value.status_code
        assert NOT_AUTHENTICATED == excinfo.value.detail

    def test_fail_to_authorize_request_due_to_missing_credentials_with_auto_error_false(
        self, empty_request: Mock
    ):
        jwt_bearer = JWTBearer(auto_error=False)
        result = jwt_bearer(empty_request)

        assert result is None

    def test_successfully_authorize_request(
        self,
        mocker,
        jwt_bearer: JWTBearer,
        jwt_token: JWTToken,
        refresh_token: str,
        token_service: TokenService,
        valid_request: Request,
    ):
        mocker.patch.object(
            TokenService,
            "get_by_id",
            return_value=(jwt_token.model_dump(), refresh_token),
        )

        result = jwt_bearer(valid_request)

        assert jwt_token.model_dump() == result.model_dump()
        token_service.get_by_id.assert_called_once_with(jwt_token.jti)

    def test_successfully_authorize_request_from_query_param(
        self,
        mocker,
        empty_request: Request,
        jwt_bearer: JWTBearer,
        jwt_token: JWTToken,
        refresh_token: str,
        settings: Settings,
        token_service: TokenService,
    ):
        mocker.patch.object(
            TokenService,
            "get_by_id",
            return_value=(jwt_token.model_dump(), refresh_token),
        )
        empty_request.query_params = {
            "token": f"{jwt.encode(jwt_token.model_dump(), settings.jwt_secret)}"
        }

        result = jwt_bearer(empty_request)

        assert jwt_token.model_dump() == result.model_dump()
        token_service.get_by_id.assert_called_once_with(jwt_token.jti)
