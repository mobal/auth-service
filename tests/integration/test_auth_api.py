import uuid
from base64 import b64encode

import jwt
import pendulum
import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.models.jwt import JWTToken, RefreshToken
from app.models.user import User


class TestAuthApi:
    @pytest.fixture
    def test_client(
        self, initialize_tokens_table, initialize_users_table, initialize_services_table
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

    def test_fail_to_login_due_to_invalid_password(
        self, token_url: str, test_client: TestClient, user: User
    ):
        response = test_client.post(
            token_url,
            data={
                "grant_type": "password",
                "username": user.email,
                "password": "asdasdasd",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["error"] == "Unauthorized"

    def test_fail_to_login_due_to_user_not_found(
        self, token_url: str, password: str, test_client: TestClient
    ):
        response = test_client.post(
            token_url,
            data={
                "grant_type": "password",
                "username": "root@gmail.com",
                "password": password,
            },
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["error"] == "The requested user was not found"

    def test_successfully_login(
        self, token_url: str, password: str, test_client: TestClient
    ):
        response = test_client.post(
            token_url,
            data={
                "grant_type": "password",
                "username": "root@squarelabs.hu",
                "password": password,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "Bearer"
        assert "expires_in" in body
        assert "scope" in body
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
        assert response.json()["error"] == "invalid_client"

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
        assert response.json()["error"] == "invalid_client"

    def test_fail_to_register_due_to_missing_bearer_token(
        self, base_url: str, test_client: TestClient
    ):
        response = test_client.post(
            f"{base_url}/register",
            json={
                "email": "newuser@squarelabs.hu",
                "username": "newuser",
                "password": "password123",
                "confirmPassword": "password123",
                "displayName": "New User",
            },
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_fail_to_register_due_to_empty_body(
        self,
        base_url: str,
        jwt_secret_ssm_param_value: str,
        jwt_token: JWTToken,
        test_client: TestClient,
    ):
        response = test_client.post(
            f"{base_url}/register",
            json={},
            headers=self._auth_header(jwt_token, jwt_secret_ssm_param_value),
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_fail_to_register_due_to_user_already_exists(
        self,
        base_url: str,
        jwt_secret_ssm_param_value: str,
        jwt_token: JWTToken,
        test_client: TestClient,
        user: User,
    ):
        response = test_client.post(
            f"{base_url}/register",
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
        base_url: str,
        jwt_secret_ssm_param_value: str,
        jwt_token: JWTToken,
        test_client: TestClient,
        user: User,
    ):
        response = test_client.post(
            f"{base_url}/register",
            json={
                "email": "newemail@squarelabs.hu",
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
        base_url: str,
        jwt_secret_ssm_param_value: str,
        jwt_token: JWTToken,
        test_client: TestClient,
    ):
        response = test_client.post(
            f"{base_url}/register",
            json={
                "email": "newuser@squarelabs.hu",
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
        base_url: str,
        jwt_secret_ssm_param_value: str,
        jwt_token: JWTToken,
        test_client: TestClient,
    ):
        response = test_client.post(
            f"{base_url}/register",
            json={
                "email": "user@squarelabs.hu",
                "username": "user",
                "password": "password123",
                "confirmPassword": "password321",
                "displayName": "User",
            },
            headers=self._auth_header(jwt_token, jwt_secret_ssm_param_value),
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert response.json()["error"] == "Validation Error"

    def test_fail_to_register_due_to_invalid_email(
        self,
        base_url: str,
        jwt_secret_ssm_param_value: str,
        jwt_token: JWTToken,
        test_client: TestClient,
    ):
        response = test_client.post(
            f"{base_url}/register",
            json={
                "email": "invalidemail",
                "username": "newuser",
                "password": "password123",
                "confirmPassword": "password123",
                "displayName": "New User",
            },
            headers=self._auth_header(jwt_token, jwt_secret_ssm_param_value),
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert response.json()["error"] == "Validation Error"

    def test_fail_to_register_due_to_missing_username(
        self,
        base_url: str,
        jwt_secret_ssm_param_value: str,
        jwt_token: JWTToken,
        test_client: TestClient,
    ):
        response = test_client.post(
            f"{base_url}/register",
            json={
                "email": "user@squarelabs.hu",
                "password": "password123",
                "confirmPassword": "password123",
                "displayName": "New User",
            },
            headers=self._auth_header(jwt_token, jwt_secret_ssm_param_value),
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert response.json()["error"] == "Validation Error"

    def test_fail_to_admin_register_due_to_missing_required_scope(
        self,
        base_url: str,
        jwt_secret_ssm_param_value: str,
        test_client: TestClient,
        tokens_table,
    ):
        iat = pendulum.now()
        exp = iat.add(hours=1)
        jwt_token_without_scope = JWTToken(
            exp=exp.int_timestamp,
            iat=iat.int_timestamp,
            iss=None,
            jti=str(uuid.uuid4()),
            sub="user-id",
            scope=None,
            user={
                "id": "user-id",
                "email": "user@squarelabs.hu",
                "username": "user",
                "roles": [],
                "created_at": iat.to_iso8601_string(),
            },
        )

        tokens_table.put_item(
            Item={
                "jti": jwt_token_without_scope.jti,
                "jwt_token": jwt_token_without_scope.model_dump(),
                "refresh_token": str(uuid.uuid4()),
                "created_at": pendulum.now().to_iso8601_string(),
                "ttl": jwt_token_without_scope.exp,
            }
        )

        response = test_client.post(
            f"{base_url}/register",
            json={
                "email": "newuser@squarelabs.hu",
                "username": "newuser",
                "password": "password123",
                "confirmPassword": "password123",
                "displayName": "New User",
            },
            headers=self._auth_header(
                jwt_token_without_scope, jwt_secret_ssm_param_value
            ),
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["error"] == "Insufficient scope"

    def test_fail_to_register_due_to_missing_email(
        self,
        base_url: str,
        jwt_secret_ssm_param_value: str,
        jwt_token: JWTToken,
        test_client: TestClient,
    ):
        response = test_client.post(
            f"{base_url}/register",
            json={
                "username": "newuser",
                "password": "password123",
                "confirmPassword": "password123",
                "displayName": "New User",
            },
            headers=self._auth_header(jwt_token, jwt_secret_ssm_param_value),
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert response.json()["error"] == "Validation Error"

    def test_successfully_admin_register_with_required_scope(
        self,
        base_url: str,
        jwt_secret_ssm_param_value: str,
        jwt_token: JWTToken,
        test_client: TestClient,
    ):
        response = test_client.post(
            f"{base_url}/register",
            json={
                "email": "rootuser@squarelabs.hu",
                "username": "rootuser",
                "password": "password123",
                "confirmPassword": "password123",
                "displayName": "Root User",
            },
            headers=self._auth_header(jwt_token, jwt_secret_ssm_param_value),
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert "Location" in response.headers
        assert response.headers["Location"].startswith("/api/v1/users/")

    def test_fail_to_register_due_to_missing_all_required_scopes(
        self,
        base_url: str,
        jwt_secret_ssm_param_value: str,
        test_client: TestClient,
        tokens_table,
    ):
        iat = pendulum.now()
        exp = iat.add(hours=1)
        jwt_token_with_other_scopes = JWTToken(
            exp=exp.int_timestamp,
            iat=iat.int_timestamp,
            iss=None,
            jti=str(uuid.uuid4()),
            sub="user-id",
            scope="posts:read posts:write",
            user={
                "id": "user-id",
                "email": "user@squarelabs.hu",
                "username": "user",
                "roles": ["moderator", "viewer"],
                "created_at": iat.to_iso8601_string(),
            },
        )

        tokens_table.put_item(
            Item={
                "jti": jwt_token_with_other_scopes.jti,
                "jwt_token": jwt_token_with_other_scopes.model_dump(),
                "refresh_token": str(uuid.uuid4()),
                "created_at": pendulum.now().to_iso8601_string(),
                "ttl": jwt_token_with_other_scopes.exp,
            }
        )

        response = test_client.post(
            f"{base_url}/register",
            json={
                "email": "newuser@squarelabs.hu",
                "username": "newuser",
                "password": "password123",
                "confirmPassword": "password123",
                "displayName": "New User",
            },
            headers=self._auth_header(
                jwt_token_with_other_scopes, jwt_secret_ssm_param_value
            ),
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["error"] == "Insufficient scope"

    def test_successfully_register_with_multiple_scopes_including_required(
        self,
        base_url: str,
        jwt_secret_ssm_param_value: str,
        test_client: TestClient,
        tokens_table,
    ):
        iat = pendulum.now()
        exp = iat.add(hours=1)
        jwt_token_with_multiple_scopes = JWTToken(
            exp=exp.int_timestamp,
            iat=iat.int_timestamp,
            iss=None,
            jti=str(uuid.uuid4()),
            sub="admin-id",
            scope="tokens:revoke users:read users:write",
            user={
                "id": "admin-id",
                "email": "admin@squarelabs.hu",
                "username": "admin",
                "roles": ["user", "root", "moderator"],
                "created_at": iat.to_iso8601_string(),
            },
        )

        tokens_table.put_item(
            Item={
                "jti": jwt_token_with_multiple_scopes.jti,
                "jwt_token": jwt_token_with_multiple_scopes.model_dump(),
                "refresh_token": str(uuid.uuid4()),
                "created_at": pendulum.now().to_iso8601_string(),
                "ttl": jwt_token_with_multiple_scopes.exp,
            }
        )

        response = test_client.post(
            f"{base_url}/register",
            json={
                "email": "multiuser@squarelabs.hu",
                "username": "multiuser",
                "password": "password123",
                "confirmPassword": "password123",
                "displayName": "Multi User",
            },
            headers=self._auth_header(
                jwt_token_with_multiple_scopes, jwt_secret_ssm_param_value
            ),
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert "Location" in response.headers
        assert response.headers["Location"].startswith("/api/v1/users/")
