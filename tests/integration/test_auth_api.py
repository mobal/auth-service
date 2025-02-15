import uuid
from typing import Dict, Optional

import jwt
import pendulum
import pytest
from fastapi import status
from httpx import Response
from respx import MockRouter, Route
from starlette.testclient import TestClient

from app.models import JWTToken


@pytest.mark.asyncio
class TestAuthApi:
    BASE_URL = "/api/v1"

    async def __generate_respx_mock(
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
    def test_client(
        self, initialize_tokens_table, initialize_users_table
    ) -> TestClient:
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
        jwt_token: JWTToken,
        respx_mock: MockRouter,
        test_client: TestClient,
        tokens_table,
    ):
        cache_service_put_keyvalue_mock = await self.__generate_respx_mock(
            "POST",
            cache_service_response_201,
            respx_mock,
            pytest.cache_service_base_url,
        )

        response = test_client.get(
            f"{self.BASE_URL}/logout",
            headers={
                "Authorization": f"Bearer {jwt.encode(jwt_token.model_dump(), pytest.jwt_secret_ssm_param_value)}"
            },
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert cache_service_put_keyvalue_mock.called
        assert cache_service_put_keyvalue_mock.call_count == 1
