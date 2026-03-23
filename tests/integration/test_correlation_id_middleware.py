import os
import uuid

import pytest
from argon2 import PasswordHasher
from fastapi import status
from fastapi.testclient import TestClient

X_CORRELATION_ID = "X-Correlation-ID"
USER_SERVICE_USERS_URL = f"{os.getenv('USER_SERVICE_BASE_URL_SSM_PARAM_VALUE')}/api/v1/users?email=root%40squarelabs.hu"
USER_VERIFY_RESPONSE = {
    "items": [
        {
            "id": str(uuid.uuid4()),
            "email": "root@squarelabs.hu",
            "roles": ["root"],
            "password": PasswordHasher().hash("password"),
        }
    ]
}


class TestCorrelationIdMiddleware:
    @pytest.fixture
    def test_client(
        self, initialize_tokens_table, initialize_services_table
    ) -> TestClient:
        from app.api_handler import app

        return TestClient(app, raise_server_exceptions=True)

    def test_correlation_id_header_is_set_in_response(
        self, httpx_mock, token_url: str, test_client: TestClient
    ):
        httpx_mock.add_response(
            method="GET",
            url=USER_SERVICE_USERS_URL,
            json=USER_VERIFY_RESPONSE,
            status_code=status.HTTP_200_OK,
        )

        response = test_client.post(
            token_url,
            data={
                "grant_type": "password",
                "username": "root@squarelabs.hu",
                "password": "password",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert X_CORRELATION_ID in response.headers
        assert response.headers[X_CORRELATION_ID] is not None

    def test_correlation_id_from_request_header_is_preserved(
        self, httpx_mock, token_url: str, test_client: TestClient
    ):
        httpx_mock.add_response(
            method="GET",
            url=USER_SERVICE_USERS_URL,
            json=USER_VERIFY_RESPONSE,
            status_code=status.HTTP_200_OK,
        )
        correlation_id_value = str(uuid.uuid4())

        response = test_client.post(
            token_url,
            data={
                "grant_type": "password",
                "username": "root@squarelabs.hu",
                "password": "password",
            },
            headers={X_CORRELATION_ID: correlation_id_value},
        )

        assert response.status_code == status.HTTP_200_OK
        assert X_CORRELATION_ID in response.headers
        assert response.headers[X_CORRELATION_ID] is not None

    def test_correlation_id_is_generated_when_not_provided(
        self, httpx_mock, token_url: str, test_client: TestClient
    ):
        httpx_mock.add_response(
            method="GET",
            url=USER_SERVICE_USERS_URL,
            json=USER_VERIFY_RESPONSE,
            status_code=status.HTTP_200_OK,
        )

        response = test_client.post(
            token_url,
            data={
                "grant_type": "password",
                "username": "root@squarelabs.hu",
                "password": "password",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        correlation_id_value = response.headers.get(X_CORRELATION_ID)
        assert correlation_id_value is not None

        try:
            uuid.UUID(correlation_id_value)
        except ValueError:
            pytest.fail(
                f"Invalid UUID format for correlation ID: {correlation_id_value}"
            )
