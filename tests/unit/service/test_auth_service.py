import uuid

import jwt
import pendulum
import pytest as pytest
from argon2 import PasswordHasher
from fastapi import HTTPException, status

from app.exceptions import (
    TokenMismatchException,
    TokenNotFoundException,
    UserNotFoundException,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.token_service import TokenService
from app.models.jwt import JWTToken
from app.settings import Settings

ALGORITHMS = ["HS256"]
PASSWORD = "123456"


class TestAuthService:
    @pytest.fixture
    def auth_service(self) -> AuthService:
        return AuthService()

    @pytest.fixture
    def jwt_token(self, user: User) -> JWTToken:
        iat = pendulum.now()
        exp = iat.add(hours=1)
        return JWTToken(
            exp=exp.int_timestamp,
            iat=iat.int_timestamp,
            jti=str(uuid.uuid4()),
            sub=user.id,
            user=user.model_dump(),
        )

    @pytest.fixture
    def password_hasher(self) -> PasswordHasher:
        return PasswordHasher()

    @pytest.fixture
    def user(self, password_hasher: PasswordHasher) -> User:
        return User(
            id=str(uuid.uuid4()),
            display_name="root",
            email="root@netcode.hu",
            password=password_hasher.hash(PASSWORD),
            username="root",
            created_at=pendulum.now().to_iso8601_string(),
        )

    def test_successfully_login(
        self,
        mocker,
        auth_service: AuthService,
        settings: Settings,
        token_service: TokenService,
        user: User,
        user_repository: UserRepository,
    ):
        mocker.patch.object(UserRepository, "get_by_email", return_value=user)
        mocker.patch.object(TokenService, "create")

        jwt_token, refresh_token = auth_service.login(user.email, PASSWORD)
        decoded_jwt_token = JWTToken(
            **jwt.decode(jwt_token, settings.jwt_secret, ALGORITHMS)
        )

        assert user.id == decoded_jwt_token.sub
        assert (
            pendulum.from_timestamp(decoded_jwt_token.exp)
            - pendulum.from_timestamp(decoded_jwt_token.iat)
        ).in_words() == "1 hour"
        user_repository.get_by_email.assert_called_once_with(user.email)
        token_service.create.assert_called_once_with(decoded_jwt_token, refresh_token)

    def test_fail_to_login_due_user_not_found_by_email(
        self,
        mocker,
        auth_service: AuthService,
        user: User,
        user_repository: UserRepository,
    ):
        error_message = "The requested user was not found"
        mocker.patch.object(UserRepository, "get_by_email", return_value=None)

        with pytest.raises(UserNotFoundException) as excinfo:
            auth_service.login(user.email, PASSWORD)

        assert status.HTTP_404_NOT_FOUND == excinfo.value.status_code
        assert error_message == excinfo.value.detail
        user_repository.get_by_email.assert_called_once_with(user.email)

    def test_fail_to_login_due_password_does_not_match(
        self,
        mocker,
        auth_service: AuthService,
        password_hasher: PasswordHasher,
        user: User,
        user_repository: UserRepository,
    ):
        mocker.patch.object(UserRepository, "get_by_email", return_value=user)

        with pytest.raises(HTTPException) as excinfo:
            auth_service.login(user.email, password_hasher.hash("doest_not_match"))

        assert status.HTTP_401_UNAUTHORIZED == excinfo.value.status_code
        assert "Unauthorized" == excinfo.value.detail
        user_repository.get_by_email.assert_called_once_with(user.email)

    def test_successfully_logout(
        self,
        mocker,
        auth_service: AuthService,
        jwt_token: JWTToken,
        token_service: TokenService,
    ):
        mocker.patch.object(TokenService, "delete_by_id")

        auth_service.logout(jwt_token)

        token_service.delete_by_id.assert_called_once_with(jwt_token.jti)

    def test_fail_to_logout_due_to_token_service_exception(
        self,
        mocker,
        auth_service: AuthService,
        jwt_token: JWTToken,
        token_service: TokenService,
    ):
        error_message = "The requested token was not found"
        mocker.patch.object(
            TokenService,
            "delete_by_id",
            side_effect=TokenNotFoundException(error_message),
        )

        with pytest.raises(TokenNotFoundException) as excinfo:
            auth_service.logout(jwt_token)

        assert status.HTTP_404_NOT_FOUND == excinfo.value.status_code
        assert error_message == excinfo.value.detail
        token_service.delete_by_id.assert_called_once_with(jwt_token.jti)

    def test_successfully_refresh_tokens(
        self,
        mocker,
        auth_service: AuthService,
        jwt_token: JWTToken,
        refresh_token: str,
        token_service: TokenService,
    ):
        item = {
            "jti": jwt_token.jti,
            "jwt_token": jwt_token.model_dump(),
            "refresh_token": refresh_token,
            "created_at": pendulum.now().to_iso8601_string(),
            "ttl": jwt_token.exp,
        }
        mocker.patch.object(TokenService, "get_by_refresh_token", return_value=item)
        mocker.patch.object(TokenService, "create")
        mocker.patch.object(TokenService, "delete_by_id")

        new_jwt_token, new_refresh_token = auth_service.refresh(
            jwt_token, refresh_token
        )

        token_service.get_by_refresh_token.assert_called_once_with(refresh_token)
        token_service.create.assert_called_once_with(
            JWTToken(
                **jwt.decode(
                    new_jwt_token,
                    pytest.jwt_secret_ssm_param_value,
                    algorithms=["HS256"],
                )
            ),
            new_refresh_token,
        )
        token_service.delete_by_id.assert_called_once_with(jwt_token.jti)

    def test_fail_to_refresh_due_to_missing_token(
        self,
        mocker,
        auth_service: AuthService,
        jwt_token: JWTToken,
        refresh_token: str,
        token_service: TokenService,
    ):
        mocker.patch.object(TokenService, "get_by_refresh_token", return_value=None)

        with pytest.raises(TokenNotFoundException) as excinfo:
            auth_service.refresh(jwt_token, refresh_token)

        assert TokenNotFoundException.__name__ == excinfo.typename
        assert "The requested token was not found" == excinfo.value.detail

        token_service.get_by_refresh_token.assert_called_once_with(refresh_token)

    def test_fail_to_refresh_token_due_to_token_mismatch(
        self,
        mocker,
        auth_service: AuthService,
        jwt_token: JWTToken,
        refresh_token: str,
        token_service: TokenService,
    ):
        now = pendulum.now().int_timestamp
        item = {
            "jti": jwt_token.jti,
            "jwt_token": {
                "exp": now,
                "iat": now,
                "iss": None,
                "jti": str(uuid.uuid4()),
                "sub": jwt_token.user["id"],
                "user": jwt_token.user,
            },
            "refresh_token": refresh_token,
            "created_at": pendulum.now().to_iso8601_string(),
            "ttl": jwt_token.exp,
        }
        mocker.patch.object(TokenService, "get_by_refresh_token", return_value=item)

        with pytest.raises(TokenMismatchException) as excinfo:
            auth_service.refresh(jwt_token, refresh_token)

        assert TokenMismatchException.__name__ == excinfo.typename
        assert "Internal Server Error" == excinfo.value.detail

        token_service.get_by_refresh_token.assert_called_once_with(refresh_token)
