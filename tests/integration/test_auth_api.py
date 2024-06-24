import uuid
from typing import Dict, Optional

import jwt
import pendulum
import pytest
from httpx import Response
from respx import MockRouter, Route
from starlette import status
from starlette.testclient import TestClient


@pytest.mark.asyncio
class TestAuthApi:
    BASE_URL = "/api/v1"

    async def _assert_response(
        self,
        cache_service_mock: MockRouter,
        message: str,
        status_code: int,
        response: Response,
    ):
        assert response.status_code == status_code
        result = response.json()
        assert result["status"] == status_code
        assert result["id"]
        assert result["message"] == message
        assert cache_service_mock.called
        assert cache_service_mock.call_count == 1

    async def _generate_jwt_token(self, role: str | None = None, exp: int = 1) -> str:
        iat = pendulum.now()
        exp = iat.add(hours=exp)
        return jwt.encode(
            {
                "exp": exp.int_timestamp,
                "iat": iat.int_timestamp,
                "jti": str(uuid.uuid4()),
                "sub": {"id": str(uuid.uuid4()), "roles": [role] if role else None},
            },
            pytest.jwt_secret,
        )

    async def _generate_respx_mock(
        self,
        method: str,
        response: Response,
        respx_mock: MockRouter,
        url: str,
        headers: Optional[Dict[str, str]] = None,
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
                "message": "Internal server error",
            },
        )

    @pytest.fixture
    def test_client(self, initialize_users_table) -> TestClient:
        from app.main import app

        return TestClient(app, raise_server_exceptions=True)

    async def test_fail_to_login_due_to_empty_body(self, test_client: TestClient):
        response = test_client.post(
            f"{self.BASE_URL}/login",
            json={},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_successfully_login(self, test_client: TestClient):
        response = test_client.post(
            f"{self.BASE_URL}/login",
            json={"email": "root@netcode.hu", "password": "12345678"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["token"]

    async def test_fail_to_logout_due_to_missing_bearer_token(
        self, test_client: TestClient
    ):
        response = test_client.get(f"{self.BASE_URL}/logout")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_successfully_logout(
        self,
        cache_service_response_201: Response,
        cache_service_response_404: Response,
        respx_mock: MockRouter,
        test_client: TestClient,
    ):
        jwt_token = await self._generate_jwt_token()
        cache_service_get_keyvalue_mock = await self._generate_respx_mock(
            "GET", cache_service_response_404, respx_mock, pytest.cache_service_base_url
        )
        cache_service_put_keyvalue_mock = await self._generate_respx_mock(
            "POST",
            cache_service_response_201,
            respx_mock,
            pytest.cache_service_base_url,
        )

        response = test_client.get(
            f"{self.BASE_URL}/logout", headers={"Authorization": f"Bearer {jwt_token}"}
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert cache_service_get_keyvalue_mock.called
        assert cache_service_get_keyvalue_mock.call_count == 1
        assert cache_service_put_keyvalue_mock.called
        assert cache_service_put_keyvalue_mock.call_count == 1
