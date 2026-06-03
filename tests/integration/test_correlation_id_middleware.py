import os
import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient

X_CORRELATION_ID = "X-Correlation-ID"
USER_SERVICE_USERS_URL = f"{os.getenv('USER_SERVICE_BASE_URL_SSM_PARAM_VALUE')}/api/v1/users?email=root%40squarelabs.hu"
USER_ID = str(uuid.uuid4())
USER_SERVICE_VALIDATE_URL = f"{os.getenv('USER_SERVICE_BASE_URL_SSM_PARAM_VALUE')}/api/v1/users/{USER_ID}/validate"
USER_VERIFY_RESPONSE = {
    "items": [
        {
            "id": USER_ID,
            "email": "root@squarelabs.hu",
            "roles": ["root"],
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
        httpx_mock.add_response(
            method="POST",
            url=USER_SERVICE_VALIDATE_URL,
            json={"id": USER_ID, "email": "root@squarelabs.hu", "roles": ["root"]},
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
        httpx_mock.add_response(
            method="POST",
            url=USER_SERVICE_VALIDATE_URL,
            json={"id": USER_ID, "email": "root@squarelabs.hu", "roles": ["root"]},
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
        assert response.headers[X_CORRELATION_ID] == correlation_id_value

    def test_correlation_id_is_generated_when_not_provided(
        self, httpx_mock, token_url: str, test_client: TestClient
    ):
        httpx_mock.add_response(
            method="GET",
            url=USER_SERVICE_USERS_URL,
            json=USER_VERIFY_RESPONSE,
            status_code=status.HTTP_200_OK,
        )
        httpx_mock.add_response(
            method="POST",
            url=USER_SERVICE_VALIDATE_URL,
            json={"id": USER_ID, "email": "root@squarelabs.hu", "roles": ["root"]},
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

    def test_correlation_id_from_aws_lambda_context(
        self,
        httpx_mock,
        token_url: str,
        initialize_tokens_table,
        initialize_services_table,
    ):
        """Test that the correlation ID falls back to AWS Lambda request ID when no header is provided."""
        from unittest.mock import Mock

        from fastapi.testclient import TestClient

        from app.api_handler import app

        aws_request_id = str(uuid.uuid4())
        mock_context = Mock()
        mock_context.aws_request_id = aws_request_id

        # Wrap the app to inject aws.context into the ASGI scope
        # before the CorrelationIdMiddleware processes the request.
        class _LambdaContextInjector:
            def __init__(self, inner):
                self.inner = inner

            async def __call__(self, scope, receive, send):
                if scope["type"] == "http":
                    scope["aws.context"] = mock_context
                await self.inner(scope, receive, send)

        wrapped_app = _LambdaContextInjector(app)
        test_client = TestClient(wrapped_app, raise_server_exceptions=True)

        httpx_mock.add_response(
            method="GET",
            url=USER_SERVICE_USERS_URL,
            json=USER_VERIFY_RESPONSE,
            status_code=status.HTTP_200_OK,
        )
        httpx_mock.add_response(
            method="POST",
            url=USER_SERVICE_VALIDATE_URL,
            json={"id": USER_ID, "email": "root@squarelabs.hu", "roles": ["root"]},
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
        assert response.headers[X_CORRELATION_ID] == aws_request_id
