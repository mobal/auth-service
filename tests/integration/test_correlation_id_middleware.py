import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient

X_CORRELATION_ID = "X-Correlation-ID"


class TestCorrelationIdMiddleware:
    @pytest.fixture
    def test_client(
        self, initialize_tokens_table, initialize_users_table
    ) -> TestClient:
        from app.api_handler import app

        return TestClient(app, raise_server_exceptions=True)

    def test_correlation_id_header_is_set_in_response(
        self, login_url: str, password: str, test_client: TestClient
    ):
        response = test_client.post(
            login_url,
            json={"email": "root@netcode.hu", "password": password},
        )

        assert response.status_code == status.HTTP_200_OK
        assert X_CORRELATION_ID in response.headers
        assert response.headers[X_CORRELATION_ID] is not None

    def test_correlation_id_from_request_header_is_preserved(
        self, login_url: str, password: str, test_client: TestClient
    ):
        correlation_id_value = str(uuid.uuid4())
        response = test_client.post(
            login_url,
            json={"email": "root@netcode.hu", "password": password},
            headers={X_CORRELATION_ID: correlation_id_value},
        )

        assert response.status_code == status.HTTP_200_OK
        assert X_CORRELATION_ID in response.headers
        assert response.headers[X_CORRELATION_ID] is not None

    def test_correlation_id_is_generated_when_not_provided(
        self, login_url: str, password: str, test_client: TestClient
    ):
        response = test_client.post(
            login_url,
            json={"email": "root@netcode.hu", "password": password},
        )

        assert response.status_code == status.HTTP_200_OK
        correlation_id_value = response.headers.get(X_CORRELATION_ID)
        assert correlation_id_value is not None

        try:
            uuid.UUID(correlation_id_value)
        except ValueError:
            pytest.fail(f"Invalid UUID format for correlation ID: {correlation_id_value}")
