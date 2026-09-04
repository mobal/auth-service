import httpx2
import pytest
from pytest_httpx2 import HTTPXMock

from app.clients.user_service_client import UserServiceClient


class TestUserServiceClient:
    @pytest.fixture
    def jwt_token(self) -> str:
        return "dummy-jwt-token"

    @pytest.fixture
    def client(self) -> UserServiceClient:
        return UserServiceClient()

    def _assert_bearer(self, request, jwt_token: str):
        auth = request.headers.get("Authorization", "")
        assert auth == f"Bearer {jwt_token}"

    def test_get_user_by_email_sends_bearer_token(
        self,
        httpx2_mock: HTTPXMock,
        client: UserServiceClient,
        user_data: dict,
        jwt_token: str,
    ):
        httpx2_mock.add_response(
            method="GET",
            url=f"http://user-service/api/v1/users?email={user_data['email']}",
            json={"items": [user_data]},
        )

        result = client.get_user_by_email(user_data["email"], jwt_token)

        assert result == user_data
        request = httpx2_mock.get_request()
        self._assert_bearer(request, jwt_token)

    def test_get_user_by_email_returns_none_when_not_found(
        self,
        httpx2_mock: HTTPXMock,
        client: UserServiceClient,
        user_data: dict,
        jwt_token: str,
    ):
        httpx2_mock.add_response(
            method="GET",
            url=f"http://user-service/api/v1/users?email={user_data['email']}",
            status_code=404,
        )

        result = client.get_user_by_email(user_data["email"], jwt_token)

        assert result is None

    def test_get_user_by_email_returns_none_when_empty_list(
        self,
        httpx2_mock: HTTPXMock,
        client: UserServiceClient,
        user_data: dict,
        jwt_token: str,
    ):
        httpx2_mock.add_response(
            method="GET",
            url=f"http://user-service/api/v1/users?email={user_data['email']}",
            json={"items": []},
        )

        result = client.get_user_by_email(user_data["email"], jwt_token)

        assert result is None

    def test_get_user_by_id_sends_bearer_token(
        self,
        httpx2_mock: HTTPXMock,
        client: UserServiceClient,
        user_data: dict,
        jwt_token: str,
    ):
        httpx2_mock.add_response(
            method="GET",
            url=f"http://user-service/api/v1/users/{user_data['id']}",
            json=user_data,
        )

        result = client.get_user_by_id(user_data["id"], jwt_token)

        assert result == user_data
        request = httpx2_mock.get_request()
        self._assert_bearer(request, jwt_token)

    def test_get_user_by_id_returns_none_when_not_found(
        self,
        httpx2_mock: HTTPXMock,
        client: UserServiceClient,
        user_id: str,
        jwt_token: str,
    ):
        httpx2_mock.add_response(
            method="GET",
            url=f"http://user-service/api/v1/users/{user_id}",
            status_code=404,
        )

        result = client.get_user_by_id(user_id, jwt_token)

        assert result is None

    def test_validate_user_password_sends_bearer_token_and_body(
        self,
        httpx2_mock: HTTPXMock,
        client: UserServiceClient,
        user_id: str,
        jwt_token: str,
    ):
        password = "password"
        httpx2_mock.add_response(
            method="POST",
            url=f"http://user-service/api/v1/users/{user_id}/validate",
            status_code=200,
            json={"id": user_id, "email": "root@squarelabs.hu", "roles": ["root"]},
        )

        result = client.validate_user_password(user_id, password, jwt_token)

        assert result is True
        request = httpx2_mock.get_request()
        self._assert_bearer(request, jwt_token)
        assert request.content.decode() == '{"password":"password"}'

    def test_validate_user_password_returns_false_on_bad_request(
        self,
        httpx2_mock: HTTPXMock,
        client: UserServiceClient,
        user_id: str,
        jwt_token: str,
    ):
        httpx2_mock.add_response(
            method="POST",
            url=f"http://user-service/api/v1/users/{user_id}/validate",
            status_code=400,
        )

        result = client.validate_user_password(user_id, "wrong_password", jwt_token)

        assert result is False

    def test_get_user_by_email_raises_on_server_error(
        self,
        httpx2_mock: HTTPXMock,
        client: UserServiceClient,
        user_data: dict,
        jwt_token: str,
    ):
        """Cover HTTPStatusError non-404 branch in get_user_by_email (lines 27-28)."""
        httpx2_mock.add_response(
            method="GET",
            url=f"http://user-service/api/v1/users?email={user_data['email']}",
            status_code=500,
        )

        with pytest.raises(httpx2.HTTPStatusError):
            client.get_user_by_email(user_data["email"], jwt_token)

    def test_get_user_by_email_raises_on_connection_error(
        self,
        httpx2_mock: HTTPXMock,
        client: UserServiceClient,
        user_data: dict,
        jwt_token: str,
    ):
        """Cover RequestError branch in get_user_by_email (lines 29-31)."""
        httpx2_mock.add_exception(
            httpx2.RequestError("Connection refused"),
            url=f"http://user-service/api/v1/users?email={user_data['email']}",
            method="GET",
        )

        with pytest.raises(httpx2.RequestError):
            client.get_user_by_email(user_data["email"], jwt_token)

    def test_validate_user_password_raises_on_server_error(
        self,
        httpx2_mock: HTTPXMock,
        client: UserServiceClient,
        user_id: str,
        jwt_token: str,
    ):
        """Cover HTTPStatusError non-400/422 branch in validate_user_password (lines 63-68)."""
        httpx2_mock.add_response(
            method="POST",
            url=f"http://user-service/api/v1/users/{user_id}/validate",
            status_code=500,
        )

        with pytest.raises(httpx2.HTTPStatusError):
            client.validate_user_password(user_id, "password", jwt_token)

    def test_validate_user_password_raises_on_connection_error(
        self,
        httpx2_mock: HTTPXMock,
        client: UserServiceClient,
        user_id: str,
        jwt_token: str,
    ):
        """Cover RequestError branch in validate_user_password (lines 69-71)."""
        httpx2_mock.add_exception(
            httpx2.RequestError("Connection refused"),
            url=f"http://user-service/api/v1/users/{user_id}/validate",
            method="POST",
        )

        with pytest.raises(httpx2.RequestError):
            client.validate_user_password(user_id, "password", jwt_token)

    def test_get_user_by_id_raises_on_server_error(
        self,
        httpx2_mock: HTTPXMock,
        client: UserServiceClient,
        user_id: str,
        jwt_token: str,
    ):
        """Cover HTTPStatusError non-404 branch in get_user_by_id (lines 90-91)."""
        httpx2_mock.add_response(
            method="GET",
            url=f"http://user-service/api/v1/users/{user_id}",
            status_code=500,
        )

        with pytest.raises(httpx2.HTTPStatusError):
            client.get_user_by_id(user_id, jwt_token)

    def test_get_user_by_id_raises_on_connection_error(
        self,
        httpx2_mock: HTTPXMock,
        client: UserServiceClient,
        user_id: str,
        jwt_token: str,
    ):
        """Cover RequestError branch in get_user_by_id (lines 92-94)."""
        httpx2_mock.add_exception(
            httpx2.RequestError("Connection refused"),
            url=f"http://user-service/api/v1/users/{user_id}",
            method="GET",
        )

        with pytest.raises(httpx2.RequestError):
            client.get_user_by_id(user_id, jwt_token)
