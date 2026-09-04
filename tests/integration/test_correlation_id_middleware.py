import os
import uuid

import pytest
from argon2 import PasswordHasher
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
    @pytest.fixture(autouse=True)
    def override_dependencies(self):
        from app.api_handler import app
        from app.clients.user_service_client import UserServiceClient
        from app.dependencies import get_auth_service, get_jwt_bearer
        from app.jwt_bearer import JWTBearer
        from app.repositories.authorization_code_repository import (
            AuthorizationCodeRepository,
        )
        from app.repositories.service_repository import ServiceRepository
        from app.repositories.token_repository import TokenRepository
        from app.services.auth_service import AuthService
        from app.services.token_service import TokenService

        hasher = PasswordHasher(time_cost=1, memory_cost=64, parallelism=1)  # noqa
        token_svc = TokenService(token_repository=TokenRepository())

        app.dependency_overrides[get_auth_service] = lambda: AuthService(
            password_hasher=hasher,
            authorization_code_repository=AuthorizationCodeRepository(),
            service_repository=ServiceRepository(),
            token_service=token_svc,
            user_service_client=UserServiceClient(),
        )
        from fastapi import Request

        from app.models.jwt import JWTToken

        def _resolve_jwt(request: Request) -> JWTToken | None:
            return JWTBearer(token_service=token_svc)(request)

        app.dependency_overrides[get_jwt_bearer] = _resolve_jwt

    @pytest.fixture
    def test_client(
        self, initialize_tokens_table, initialize_services_table
    ) -> TestClient:
        from app.api_handler import app

        return TestClient(app, raise_server_exceptions=True)

    def test_correlation_id_header_is_set_in_response(
        self, httpx2_mock, token_url: str, test_client: TestClient
    ):
        httpx2_mock.add_response(
            method="GET",
            url=USER_SERVICE_USERS_URL,
            json=USER_VERIFY_RESPONSE,
            status_code=status.HTTP_200_OK,
        )
        httpx2_mock.add_response(
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
        self, httpx2_mock, token_url: str, test_client: TestClient
    ):
        httpx2_mock.add_response(
            method="GET",
            url=USER_SERVICE_USERS_URL,
            json=USER_VERIFY_RESPONSE,
            status_code=status.HTTP_200_OK,
        )
        httpx2_mock.add_response(
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
        self, httpx2_mock, token_url: str, test_client: TestClient
    ):
        httpx2_mock.add_response(
            method="GET",
            url=USER_SERVICE_USERS_URL,
            json=USER_VERIFY_RESPONSE,
            status_code=status.HTTP_200_OK,
        )
        httpx2_mock.add_response(
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
        httpx2_mock,
        token_url: str,
        initialize_tokens_table,
        initialize_services_table,
    ):
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

        httpx2_mock.add_response(
            method="GET",
            url=USER_SERVICE_USERS_URL,
            json=USER_VERIFY_RESPONSE,
            status_code=status.HTTP_200_OK,
        )
        httpx2_mock.add_response(
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
