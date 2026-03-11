import uuid
from base64 import b64encode

import jwt
import pendulum
import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.models.jwt import JWTToken, RefreshToken


class TestAuthApi:
    @pytest.fixture
    def test_client(
        self,
        initialize_tokens_table,
        initialize_services_table,
        initialize_authorization_codes_table,
    ) -> TestClient:
        from app.api_handler import app

        return TestClient(app, raise_server_exceptions=True)

    def _auth_header(
        self, jwt_token: JWTToken, jwt_secret_ssm_param_value: str
    ) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {jwt.encode(jwt_token.model_dump(exclude_none=True), jwt_secret_ssm_param_value)}"
        }

    @staticmethod
    def _assert_cache_headers(response):
        assert response.headers.get("Cache-Control") == "no-store"
        assert response.headers.get("Pragma") == "no-cache"

    def test_fail_to_login_due_to_empty_body(
        self, token_url: str, test_client: TestClient
    ):
        response = test_client.post(token_url, data={})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_fail_to_login_due_to_invalid_credentials(
        self,
        httpx_mock,
        token_url: str,
        test_client: TestClient,
    ):
        import os

        httpx_mock.add_response(
            method="GET",
            url=f"{os.getenv('USER_SERVICE_BASE_URL_SSM_PARAM_VALUE')}/users?email=root%40squarelabs.hu",
            json=[],
            status_code=status.HTTP_200_OK,
        )

        response = test_client.post(
            token_url,
            data={
                "grant_type": "password",
                "username": "root@squarelabs.hu",
                "password": "wrong_password",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["error"] == "Unauthorized"

    def test_successfully_login(
        self,
        httpx_mock,
        token_url: str,
        test_client: TestClient,
    ):
        import os
        import uuid

        from argon2 import PasswordHasher

        user_id = str(uuid.uuid4())
        httpx_mock.add_response(
            method="GET",
            url=f"{os.getenv('USER_SERVICE_BASE_URL_SSM_PARAM_VALUE')}/users?email=root%40squarelabs.hu",
            json=[
                {
                    "id": user_id,
                    "email": "root@squarelabs.hu",
                    "roles": ["root"],
                    "password": PasswordHasher().hash("password"),
                }
            ],
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
        body = response.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "Bearer"
        assert "expires_in" in body
        self._assert_cache_headers(response)

    def test_fail_to_logout_due_to_missing_bearer_token(
        self, revoke_url: str, test_client: TestClient
    ):
        response = test_client.post(revoke_url, data={"token": "dummy"})

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_successfully_logout(
        self,
        revoke_url: str,
        jwt_token: JWTToken,
        jwt_secret_ssm_param_value: str,
        test_client: TestClient,
    ):
        response = test_client.post(
            revoke_url,
            data={
                "token": jwt.encode(
                    jwt_token.model_dump(exclude_none=True), jwt_secret_ssm_param_value
                )
            },
            headers=self._auth_header(jwt_token, jwt_secret_ssm_param_value),
        )

        assert response.status_code == status.HTTP_200_OK

    def test_fail_to_refresh_due_to_missing_refresh_token(
        self, token_url: str, test_client: TestClient
    ):
        response = test_client.post(token_url, data={"grant_type": "refresh_token"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["error"] == "Invalid request: refresh_token is required"

    def test_fail_to_refresh_due_to_refresh_token_not_found(
        self,
        token_url: str,
        test_client: TestClient,
    ):
        response = test_client.post(
            token_url,
            data={"grant_type": "refresh_token", "refresh_token": str(uuid.uuid4())},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["error"] == "The requested token was not found"

    def test_fail_to_refresh_due_to_expired_token(
        self,
        dynamodb_resource,
        jwt_token: JWTToken,
        refresh_token: RefreshToken,
        token_url: str,
        test_client: TestClient,
        tokens_table_name: str,
    ):
        expired_ttl = pendulum.now().subtract(days=1).int_timestamp
        tokens_table = dynamodb_resource.Table(tokens_table_name)
        tokens_table.put_item(
            Item={
                "jti": jwt_token.jti,
                "jwt_token": jwt_token.model_dump(),
                "refresh_token": refresh_token.token,
                "created_at": pendulum.from_timestamp(
                    jwt_token.iat
                ).to_iso8601_string(),
                "expire_at": pendulum.from_timestamp(expired_ttl).to_iso8601_string(),
                "ttl": expired_ttl,
            }
        )

        response = test_client.post(
            token_url,
            data={"grant_type": "refresh_token", "refresh_token": refresh_token.token},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["error"] == "The requested token has expired"

    def test_successfully_refresh(
        self,
        refresh_token: RefreshToken,
        token_url: str,
        test_client: TestClient,
    ):
        response = test_client.post(
            token_url,
            data={"grant_type": "refresh_token", "refresh_token": refresh_token.token},
        )

        assert response.status_code == status.HTTP_200_OK
        self._assert_cache_headers(response)

    def test_successfully_client_credentials(
        self, token_url: str, password: str, service_credential, test_client: TestClient
    ):
        basic = b64encode(f"{service_credential.id}:{password}".encode()).decode()
        response = test_client.post(
            token_url,
            data={"grant_type": "client_credentials"},
            headers={"Authorization": f"Basic {basic}"},
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert "access_token" in body
        assert "refresh_token" not in body
        assert body["token_type"] == "Bearer"
        assert "expires_in" in body
        assert body["scope"] == "users:read users:write"
        self._assert_cache_headers(response)

    def test_fail_to_client_credentials_due_to_malformed_basic_auth(
        self, token_url: str, test_client: TestClient
    ):
        response = test_client.post(
            token_url,
            data={"grant_type": "client_credentials"},
            headers={"Authorization": "Basic !!!"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.headers["www-authenticate"] == "Basic"
        assert (
            response.json()["error"]
            == "Invalid client: missing or invalid Authorization header"
        )

    def test_fail_to_client_credentials_due_to_missing_secret_in_basic_auth(
        self, token_url: str, service_credential, test_client: TestClient
    ):
        basic = b64encode(service_credential.id.encode()).decode()
        response = test_client.post(
            token_url,
            data={"grant_type": "client_credentials"},
            headers={"Authorization": f"Basic {basic}"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.headers["www-authenticate"] == "Basic"
        assert (
            response.json()["error"]
            == "Invalid client: missing or invalid Authorization header"
        )

    def test_fail_to_client_credentials_due_to_missing_authorization_header(
        self, token_url: str, test_client: TestClient
    ):
        response = test_client.post(
            token_url,
            data={"grant_type": "client_credentials"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.headers["www-authenticate"] == "Basic"
        assert (
            response.json()["error"]
            == "Invalid client: missing or invalid Authorization header"
        )

    def test_fail_to_login_due_to_missing_credentials(
        self, token_url: str, test_client: TestClient
    ):
        response = test_client.post(
            token_url,
            data={"grant_type": "password", "username": "root@squarelabs.hu"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert (
            response.json()["error"]
            == "Invalid request: username and password are required"
        )

    def test_fail_to_token_due_to_unsupported_grant_type(
        self, token_url: str, test_client: TestClient
    ):
        response = test_client.post(
            token_url,
            data={"grant_type": "device_code"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["error"] == "Unsupported grant type"

    def test_fail_to_authorization_code_exchange_due_to_missing_code(
        self, token_url: str, test_client: TestClient
    ):
        response = test_client.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "redirect_uri": "https://example.com/callback",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert (
            response.json()["error"]
            == "Invalid request: code and redirect_uri are required"
        )

    def test_successfully_authorization_code_exchange(
        self,
        httpx_mock,
        dynamodb_resource,
        authorization_codes_table_name: str,
        token_url: str,
        test_client: TestClient,
    ):
        import os

        user_id = str(uuid.uuid4())
        redirect_uri = "https://example.com/callback"
        code = "test-auth-code-abc123"

        auth_codes_table = dynamodb_resource.Table(authorization_codes_table_name)
        auth_codes_table.put_item(
            Item={
                "id": str(uuid.uuid4()),
                "code": code,
                "client_id": "my-app",
                "user_id": user_id,
                "redirect_uri": redirect_uri,
                "scope": "users:read",
                "ttl": pendulum.now().add(minutes=10).int_timestamp,
            }
        )

        httpx_mock.add_response(
            method="GET",
            url=f"{os.getenv('USER_SERVICE_BASE_URL_SSM_PARAM_VALUE')}/users/{user_id}",
            json={"id": user_id, "email": "root@squarelabs.hu", "roles": ["root"]},
            status_code=status.HTTP_200_OK,
        )

        response = test_client.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "Bearer"
        assert "expires_in" in body
        self._assert_cache_headers(response)

    def test_successfully_authorize(
        self,
        httpx_mock,
        jwt_token: JWTToken,
        jwt_secret_ssm_param_value: str,
        authorize_url: str,
        test_client: TestClient,
    ):
        import os

        httpx_mock.add_response(
            method="GET",
            url=f"{os.getenv('USER_SERVICE_BASE_URL_SSM_PARAM_VALUE')}/users/{jwt_token.sub}",
            json={
                "id": jwt_token.sub,
                "email": "root@squarelabs.hu",
                "roles": ["root"],
            },
            status_code=status.HTTP_200_OK,
        )

        response = test_client.get(
            authorize_url,
            params={
                "response_type": "code",
                "client_id": "my-app",
                "redirect_uri": "https://example.com/callback",
                "scope": "users:read",
                "state": "xyz123",
            },
            headers=self._auth_header(jwt_token, jwt_secret_ssm_param_value),
            follow_redirects=False,
        )

        assert response.status_code == status.HTTP_302_FOUND
        location = response.headers["location"]
        assert location.startswith("https://example.com/callback?")
        assert "code=" in location
        assert "state=xyz123" in location

    def test_fail_to_authorize_due_to_invalid_response_type(
        self,
        jwt_token: JWTToken,
        jwt_secret_ssm_param_value: str,
        authorize_url: str,
        test_client: TestClient,
    ):
        response = test_client.get(
            authorize_url,
            params={
                "response_type": "token",
                "client_id": "my-app",
                "redirect_uri": "https://example.com/callback",
            },
            headers=self._auth_header(jwt_token, jwt_secret_ssm_param_value),
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["error"] == "Unsupported grant type"
