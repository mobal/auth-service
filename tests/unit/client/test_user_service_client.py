import uuid

import jwt
import pendulum
import pytest
from pytest_httpx import HTTPXMock

from app.clients.user_service_client import UserServiceClient
from app.settings import Settings


class TestUserServiceClient:
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

    def _decode_bearer(self, request, settings: Settings) -> dict:
        auth = request.headers.get("Authorization", "")
        assert auth.startswith("Bearer "), "Missing Bearer token"
        token = auth.removeprefix("Bearer ")
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])

    def test_get_user_by_email_sends_bearer_token(
        self,
        httpx_mock: HTTPXMock,
        client: UserServiceClient,
        user_data: dict,
        settings: Settings,
    ):
        httpx_mock.add_response(
            method="GET",
            url=f"http://user-service/users?email={user_data['email']}",
            json=[user_data],
        )

        result = client.get_user_by_email(user_data["email"])

        assert result == user_data
        request = httpx_mock.get_request()
        decoded = self._decode_bearer(request, settings)
        assert decoded["sub"] == "auth-service"

    def test_get_user_by_email_returns_none_when_not_found(
        self,
        client: UserServiceClient,
        user_data: dict,
        monkeypatch,
    ):
        import httpx

        def raise_404(*args, **kwargs):
            response = httpx.Response(status_code=404)
            raise httpx.HTTPStatusError(
                "404", request=httpx.Request("GET", ""), response=response
            )

        monkeypatch.setattr("httpx.get", raise_404)

        result = client.get_user_by_email(user_data["email"])

        assert result is None

    def test_get_user_by_email_returns_none_when_empty_list(
        self,
        httpx_mock: HTTPXMock,
        client: UserServiceClient,
        user_data: dict,
    ):
        httpx_mock.add_response(
            method="GET",
            url=f"http://user-service/users?email={user_data['email']}",
            json=[],
        )

        result = client.get_user_by_email(user_data["email"])

        assert result is None

    def test_get_user_by_id_sends_bearer_token(
        self,
        httpx_mock: HTTPXMock,
        client: UserServiceClient,
        user_data: dict,
        settings: Settings,
    ):
        httpx_mock.add_response(
            method="GET",
            url=f"http://user-service/users/{user_data['id']}",
            json=user_data,
        )

        result = client.get_user_by_id(user_data["id"])

        assert result == user_data
        request = httpx_mock.get_request()
        decoded = self._decode_bearer(request, settings)
        assert decoded["sub"] == "auth-service"

    def test_get_user_by_id_returns_none_when_not_found(
        self,
        client: UserServiceClient,
        user_id: str,
        monkeypatch,
    ):
        import httpx

        def raise_404(*args, **kwargs):
            response = httpx.Response(status_code=404)
            raise httpx.HTTPStatusError(
                "404", request=httpx.Request("GET", ""), response=response
            )

        monkeypatch.setattr("httpx.get", raise_404)

        result = client.get_user_by_id(user_id)

        assert result is None

    def test_access_token_is_cached(
        self,
        httpx_mock: HTTPXMock,
        client: UserServiceClient,
        user_data: dict,
    ):
        httpx_mock.add_response(
            method="GET",
            url=f"http://user-service/users/{user_data['id']}",
            json=user_data,
        )
        httpx_mock.add_response(
            method="GET",
            url=f"http://user-service/users/{user_data['id']}",
            json=user_data,
        )

        client.get_user_by_id(user_data["id"])
        first_token = client._jwt_token

        client.get_user_by_id(user_data["id"])
        second_token = client._jwt_token

        assert first_token == second_token

    def test_access_token_is_refreshed_when_expired(
        self,
        httpx_mock: HTTPXMock,
        client: UserServiceClient,
        user_data: dict,
    ):
        httpx_mock.add_response(
            method="GET",
            url=f"http://user-service/users/{user_data['id']}",
            json=user_data,
        )
        httpx_mock.add_response(
            method="GET",
            url=f"http://user-service/users/{user_data['id']}",
            json=user_data,
        )

        client.get_user_by_id(user_data["id"])
        first_token = client._jwt_token

        client._jwt_token_expires_at = pendulum.now().subtract(seconds=1).int_timestamp

        client.get_user_by_id(user_data["id"])
        second_token = client._jwt_token

        assert first_token != second_token
