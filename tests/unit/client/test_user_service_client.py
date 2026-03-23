import uuid

import pytest
from pytest_httpx import HTTPXMock

from app.clients.user_service_client import UserServiceClient


class TestUserServiceClient:
    @pytest.fixture
    def jwt_token(self) -> str:
        return "dummy-jwt-token"

    @pytest.fixture
    def client(self) -> UserServiceClient:
        return UserServiceClient()

    @pytest.fixture
    def user_id(self) -> str:
        return str(uuid.uuid4())

    @pytest.fixture
    def user_data(self, user_id: str) -> dict:
        return {
            "id": user_id,
            "email": "root@squarelabs.hu",
            "username": "root",
            "display_name": "root",
            "roles": ["root"],
        }

    def _assert_bearer(self, request, jwt_token: str):
        auth = request.headers.get("Authorization", "")
        assert auth == f"Bearer {jwt_token}"

    def test_get_user_by_email_sends_bearer_token(
        self,
        httpx_mock: HTTPXMock,
        client: UserServiceClient,
        user_data: dict,
        jwt_token: str,
    ):
        httpx_mock.add_response(
            method="GET",
            url=f"http://user-service/api/v1/users?email={user_data['email']}",
            json={"items": [user_data]},
        )

        result = client.get_user_by_email(user_data["email"], jwt_token)

        assert result == user_data
        request = httpx_mock.get_request()
        self._assert_bearer(request, jwt_token)

    def test_get_user_by_email_returns_none_when_not_found(
        self,
        client: UserServiceClient,
        user_data: dict,
        jwt_token: str,
        monkeypatch,
    ):
        import httpx

        def raise_404(*args, **kwargs):
            response = httpx.Response(status_code=404)
            raise httpx.HTTPStatusError(
                "404", request=httpx.Request("GET", ""), response=response
            )

        monkeypatch.setattr("httpx.get", raise_404)

        result = client.get_user_by_email(user_data["email"], jwt_token)

        assert result is None

    def test_get_user_by_email_returns_none_when_empty_list(
        self,
        httpx_mock: HTTPXMock,
        client: UserServiceClient,
        user_data: dict,
        jwt_token: str,
    ):
        httpx_mock.add_response(
            method="GET",
            url=f"http://user-service/api/v1/users?email={user_data['email']}",
            json={"items": []},
        )

        result = client.get_user_by_email(user_data["email"], jwt_token)

        assert result is None

    def test_get_user_by_id_sends_bearer_token(
        self,
        httpx_mock: HTTPXMock,
        client: UserServiceClient,
        user_data: dict,
        jwt_token: str,
    ):
        httpx_mock.add_response(
            method="GET",
            url=f"http://user-service/api/v1/users/{user_data['id']}",
            json=user_data,
        )

        result = client.get_user_by_id(user_data["id"], jwt_token)

        assert result == user_data
        request = httpx_mock.get_request()
        self._assert_bearer(request, jwt_token)

    def test_get_user_by_id_returns_none_when_not_found(
        self,
        client: UserServiceClient,
        user_id: str,
        jwt_token: str,
        monkeypatch,
    ):
        import httpx

        def raise_404(*args, **kwargs):
            response = httpx.Response(status_code=404)
            raise httpx.HTTPStatusError(
                "404", request=httpx.Request("GET", ""), response=response
            )

        monkeypatch.setattr("httpx.get", raise_404)

        result = client.get_user_by_id(user_id, jwt_token)

        assert result is None
