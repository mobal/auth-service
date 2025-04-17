import uuid

import jwt
import pendulum
import pytest
from fastapi import status
from httpx import Response
from moto.ec2.utils import random_spot_fleet_request_id
from respx import MockRouter, Route
from starlette.testclient import TestClient

from app.models import JWTToken, User

BASE_URL = "/api/v1"
LOGIN_URL = f"{BASE_URL}/login"
PASSWORD = "12345678"
REFRESH_URL = f"{BASE_URL}/refresh"


@pytest.mark.asyncio
class TestAuthApi:

    async def _generate_respx_mock(
        self,
        method: str,
        response: Response,
        respx_mock: MockRouter,
        url: str,
        headers: dict[str, str] | None = None,
    ) -> Route:
        return respx_mock.route(
            headers=headers, method=method, url__startswith=url
        ).mock(response)

    @pytest.fixture
    def cache_service_response_201(self) -> Response:
        return Response(
            status_code=status.HTTP_201_CREATED,
            json={
                "key": "jti_",
                "value": "value",
                "createdAt": pendulum.now().to_iso8601_string(),
            },
        )

    @pytest.fixture
    def cache_service_response_404(self) -> Response:
        return Response(
            status_code=status.HTTP_404_NOT_FOUND,
            json={
                "status": status.HTTP_404_NOT_FOUND,
                "id": str(uuid.uuid4()),
                "message": "Not found",
            },
        )

    @pytest.fixture
    def cache_service_response_500(self) -> Response:
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            json={
                "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "id": str(uuid.uuid4()),
                "message": "Internal Server Error",
            },
        )

    @pytest.fixture
    def test_client(
        self, initialize_tokens_table, initialize_users_table
    ) -> TestClient:
        from app.main import app

        return TestClient(app, raise_server_exceptions=True)

    async def test_fail_to_login_due_to_empty_body(self, test_client: TestClient):
        response = test_client.post(
            f"{BASE_URL}/login",
            json={},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_fail_to_login_due_to_invalid_password(
        self, test_client: TestClient, user: User
    ):
        response = test_client.post(
            LOGIN_URL, json={"email": user.email, "password": "asd"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["message"] == "Unauthorized"

    async def test_fail_to_login_due_to_user_not_found(
        self, test_client: TestClient, user: User
    ):
        response = test_client.post(
            LOGIN_URL, json={"email": "root@gmail.com", "password": PASSWORD}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["message"] == "The requested user was not found"

    async def test_successfully_login(self, test_client: TestClient):
        response = test_client.post(
            LOGIN_URL,
            json={"email": "root@netcode.hu", "password": PASSWORD},
        )

        assert response.status_code == status.HTTP_200_OK
        assert list(response.json().keys()) == ["token", "refreshToken"]

    async def test_fail_to_logout_due_to_missing_bearer_token(
        self, test_client: TestClient
    ):
        response = test_client.get(f"{BASE_URL}/logout")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_successfully_logout(
        self,
        cache_service_response_201: Response,
        jwt_token: JWTToken,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        cache_service_put_keyvalue_mock = await self._generate_respx_mock(
            "POST",
            cache_service_response_201,
            respx_mock,
            pytest.cache_service_base_url,
        )

        response = test_client.get(
            f"{BASE_URL}/logout",
            headers={
                "Authorization": f"Bearer {jwt.encode(jwt_token.model_dump(), pytest.jwt_secret_ssm_param_value)}"
            },
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert cache_service_put_keyvalue_mock.called
        assert cache_service_put_keyvalue_mock.call_count == 1

    async def test_fail_to_logout_due_to_cache_service_exception(
        self,
        cache_service_response_500: Response,
        jwt_token: JWTToken,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        cache_service_put_keyvalue_mock = await self._generate_respx_mock(
            "POST",
            cache_service_response_500,
            respx_mock,
            pytest.cache_service_base_url,
        )

        response = test_client.get(
            f"{BASE_URL}/logout",
            headers={
                "Authorization": f"Bearer {jwt.encode(jwt_token.model_dump(), pytest.jwt_secret_ssm_param_value)}"
            },
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["status"] == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["message"] == "Internal Server Error"
        assert cache_service_put_keyvalue_mock.called
        assert cache_service_put_keyvalue_mock.call_count == 1

    async def test_fail_to_refresh_due_to_jwt_token_not_found(
        self,
        jwt_token: JWTToken,
        refresh_token: str,
        test_client: TestClient,
    ):
        jwt_token.jti = str(uuid.uuid4())

        response = test_client.post(
            REFRESH_URL,
            json={"refreshToken": refresh_token},
            headers={
                "Authorization": f"Bearer {jwt.encode(jwt_token.model_dump(), pytest.jwt_secret_ssm_param_value)}"
            },
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["message"] == "Not authenticated"

    async def test_fail_to_refresh_due_to_jwt_token_mismatch(
        self,
        jwt_token: JWTToken,
        refresh_token: str,
        test_client: TestClient,
    ):
        jwt_token.user = {}

        response = test_client.post(
            REFRESH_URL,
            json={"refreshToken": refresh_token},
            headers={
                "Authorization": f"Bearer {jwt.encode(jwt_token.model_dump(), pytest.jwt_secret_ssm_param_value)}"
            },
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    async def test_fail_to_refresh_due_to_refresh_token_not_found(
        self,
        jwt_token: JWTToken,
        test_client: TestClient,
    ):
        response = test_client.post(
            REFRESH_URL,
            json={"refreshToken": str(uuid.uuid4())},
            headers={
                "Authorization": f"Bearer {jwt.encode(jwt_token.model_dump(), pytest.jwt_secret_ssm_param_value)}"
            },
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["message"] == "The requested token was not found"

    async def test_successfully_refresh(
        self,
        cache_service_response_201,
        jwt_token: JWTToken,
        refresh_token: str,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        cache_service_put_keyvalue_mock = await self._generate_respx_mock(
            "POST",
            cache_service_response_201,
            respx_mock,
            pytest.cache_service_base_url,
        )

        response = test_client.post(
            REFRESH_URL,
            json={"refreshToken": refresh_token},
            headers={
                "Authorization": f"Bearer {jwt.encode(jwt_token.model_dump(), pytest.jwt_secret_ssm_param_value)}"
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert cache_service_put_keyvalue_mock.called
        assert cache_service_put_keyvalue_mock.call_count == 1
