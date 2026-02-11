import uuid

import jwt
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from httpx import Response
from respx import MockRouter, Route

from app.models.jwt import JWTToken
from app.models.user import User

BASE_URL = "/api/v1"
LOGIN_URL = f"{BASE_URL}/login"
PASSWORD = "12345678"
REFRESH_URL = f"{BASE_URL}/refresh"


class TestAuthApi:
    def _generate_respx_mock(
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
    def test_client(
        self, initialize_tokens_table, initialize_users_table
    ) -> TestClient:
        from app.api_handler import app

        return TestClient(app, raise_server_exceptions=True)

    def _auth_header(
        self, jwt_token: JWTToken, jwt_secret_ssm_param_value: str
    ) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {jwt.encode(jwt_token.model_dump(exclude_none=True), jwt_secret_ssm_param_value)}"
        }

    def test_fail_to_login_due_to_empty_body(self, test_client: TestClient):
        response = test_client.post(
            f"{BASE_URL}/login",
            json={},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_fail_to_login_due_to_invalid_password(
        self, test_client: TestClient, user: User
    ):
        response = test_client.post(
            LOGIN_URL, json={"email": user.email, "password": "asd"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["error"] == "Unauthorized"

    def test_fail_to_login_due_to_user_not_found(
        self, test_client: TestClient, user: User
    ):
        response = test_client.post(
            LOGIN_URL, json={"email": "root@gmail.com", "password": PASSWORD}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["error"] == "The requested user was not found"

    def test_successfully_login(self, test_client: TestClient):
        response = test_client.post(
            LOGIN_URL,
            json={"email": "root@netcode.hu", "password": PASSWORD},
        )

        assert response.status_code == status.HTTP_200_OK
        assert list(response.json().keys()) == [
            "access_token",
            "refresh_token",
            "token_type",
            "expires_in",
        ]

    def test_fail_to_logout_due_to_missing_bearer_token(self, test_client: TestClient):
        response = test_client.get(f"{BASE_URL}/logout")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_successfully_logout(
        self,
        jwt_token: JWTToken,
        respx_mock: MockRouter,
        test_client: TestClient,
        jwt_secret_ssm_param_value: str,
    ):
        response = test_client.get(
            f"{BASE_URL}/logout",
            headers=self._auth_header(jwt_token, jwt_secret_ssm_param_value),
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_fail_to_refresh_due_to_jwt_token_not_found(
        self,
        jwt_token: JWTToken,
        refresh_token: str,
        test_client: TestClient,
        jwt_secret_ssm_param_value: str,
    ):
        jwt_token.jti = str(uuid.uuid4())

        response = test_client.post(
            REFRESH_URL,
            json={"refreshToken": refresh_token},
            headers=self._auth_header(jwt_token, jwt_secret_ssm_param_value),
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["error"] == "Not authenticated"

    def test_fail_to_refresh_due_to_jwt_token_mismatch(
        self,
        jwt_token: JWTToken,
        refresh_token: str,
        test_client: TestClient,
        jwt_secret_ssm_param_value: str,
    ):
        jwt_token.user = {}

        response = test_client.post(
            REFRESH_URL,
            json={"refreshToken": refresh_token},
            headers=self._auth_header(jwt_token, jwt_secret_ssm_param_value),
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_fail_to_refresh_due_to_refresh_token_not_found(
        self,
        jwt_token: JWTToken,
        test_client: TestClient,
        jwt_secret_ssm_param_value: str,
    ):
        response = test_client.post(
            REFRESH_URL,
            json={"refreshToken": str(uuid.uuid4())},
            headers=self._auth_header(jwt_token, jwt_secret_ssm_param_value),
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["error"] == "The requested token was not found"

    def test_successfully_refresh(
        self,
        jwt_token: JWTToken,
        refresh_token: str,
        respx_mock: MockRouter,
        test_client: TestClient,
        jwt_secret_ssm_param_value: str,
    ):
        response = test_client.post(
            REFRESH_URL,
            json={"refreshToken": refresh_token},
            headers=self._auth_header(jwt_token, jwt_secret_ssm_param_value),
        )

        assert response.status_code == status.HTTP_200_OK

    def test_fail_to_register_due_to_missing_bearer_token(
        self, test_client: TestClient
    ):
        response = test_client.post(
            f"{BASE_URL}/register",
            json={
                "email": "newuser@netcode.hu",
                "username": "newuser",
                "password": "password123",
                "confirmPassword": "password123",
                "displayName": "New User",
            },
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_fail_to_register_due_to_empty_body(
        self,
        jwt_token: JWTToken,
        test_client: TestClient,
        jwt_secret_ssm_param_value: str,
    ):
        response = test_client.post(
            f"{BASE_URL}/register",
            json={},
            headers=self._auth_header(jwt_token, jwt_secret_ssm_param_value),
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_fail_to_register_due_to_user_already_exists(
        self,
        jwt_token: JWTToken,
        test_client: TestClient,
        user: User,
        jwt_secret_ssm_param_value: str,
    ):
        response = test_client.post(
            f"{BASE_URL}/register",
            json={
                "email": user.email,
                "username": "newusername",
                "password": "password123",
                "confirmPassword": "password123",
                "displayName": "New User",
            },
            headers=self._auth_header(jwt_token, jwt_secret_ssm_param_value),
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert (
            response.json()["error"] == f"User with email {user.email} already exists"
        )

    def test_fail_to_register_due_to_username_already_exists(
        self,
        jwt_token: JWTToken,
        test_client: TestClient,
        user: User,
        jwt_secret_ssm_param_value: str,
    ):
        response = test_client.post(
            f"{BASE_URL}/register",
            json={
                "email": "newemail@netcode.hu",
                "username": user.username,
                "password": "password123",
                "confirmPassword": "password123",
                "displayName": "New User",
            },
            headers=self._auth_header(jwt_token, jwt_secret_ssm_param_value),
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert (
            response.json()["error"]
            == f"User with username {user.username} already exists"
        )

    def test_successfully_register(
        self,
        jwt_token: JWTToken,
        test_client: TestClient,
        jwt_secret_ssm_param_value: str,
    ):
        response = test_client.post(
            f"{BASE_URL}/register",
            json={
                "email": "newuser@netcode.hu",
                "username": "newuser",
                "password": "password123",
                "confirmPassword": "password123",
                "displayName": "New User",
            },
            headers=self._auth_header(jwt_token, jwt_secret_ssm_param_value),
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert "Location" in response.headers
        assert response.headers["Location"].startswith("/api/v1/users/")

    def test_fail_to_register_due_to_password_mismatch(
        self,
        jwt_token: JWTToken,
        test_client: TestClient,
        jwt_secret_ssm_param_value: str,
    ):
        response = test_client.post(
            f"{BASE_URL}/register",
            json={
                "email": "user@netcode.hu",
                "username": "user",
                "password": "password123",
                "confirmPassword": "password321",
                "displayName": "User",
            },
            headers=self._auth_header(jwt_token, jwt_secret_ssm_param_value),
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert response.json()["error"] == "Validation Error"

    def test_fail_to_register_due_to_invalid_email(
        self,
        jwt_token: JWTToken,
        test_client: TestClient,
        jwt_secret_ssm_param_value: str,
    ):
        response = test_client.post(
            f"{BASE_URL}/register",
            json={
                "email": "invalidemail",
                "username": "newuser",
                "password": "password123",
                "confirmPassword": "password123",
                "displayName": "New User",
            },
            headers=self._auth_header(jwt_token, jwt_secret_ssm_param_value),
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert response.json()["error"] == "Validation Error"

    def test_fail_to_register_due_to_missing_username(
        self,
        jwt_token: JWTToken,
        test_client: TestClient,
        jwt_secret_ssm_param_value: str,
    ):
        response = test_client.post(
            f"{BASE_URL}/register",
            json={
                "email": "user@netcode.hu",
                "password": "password123",
                "confirmPassword": "password123",
                "displayName": "New User",
            },
            headers=self._auth_header(jwt_token, jwt_secret_ssm_param_value),
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert response.json()["error"] == "Validation Error"

    def test_fail_to_register_due_to_missing_email(
        self,
        jwt_token: JWTToken,
        test_client: TestClient,
        jwt_secret_ssm_param_value: str,
    ):
        response = test_client.post(
            f"{BASE_URL}/register",
            json={
                "username": "newuser",
                "password": "password123",
                "confirmPassword": "password123",
                "displayName": "New User",
            },
            headers=self._auth_header(jwt_token, jwt_secret_ssm_param_value),
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert response.json()["error"] == "Validation Error"
