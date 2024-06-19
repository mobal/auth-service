import uuid

import jwt
import pendulum
import pytest as pytest
from argon2 import PasswordHasher
from fastapi import HTTPException
from starlette import status

from app.exceptions import CacheServiceException, UserNotFoundException
from app.models import User
from app.repositories import UserRepository
from app.services import AuthService, CacheService, JWTToken
from app.settings import Settings


@pytest.mark.asyncio
class TestAuthService:
    PASSWORD = "123456"

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
            sub=user,
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
            password=password_hasher.hash(self.PASSWORD),
            roles=["root"],
            username="root",
            created_at=pendulum.now().to_iso8601_string(),
        )

    async def test_successfully_login(
        self,
        mocker,
        auth_service: AuthService,
        settings: Settings,
        user: User,
        user_repository: UserRepository,
    ):
        mocker.patch.object(UserRepository, "get_by_email", return_value=user)

        token = await auth_service.login(user.email, self.PASSWORD)

        decoded_token = jwt.decode(token.token, settings.jwt_secret, ["HS256"])
        user_dict = user.model_dump(
            exclude=["id", "created_at", "deleted_at", "password", "updated_at"]
        )

        assert user_dict == decoded_token["sub"]
        assert (
            pendulum.from_timestamp(decoded_token.get("exp"))
            - pendulum.from_timestamp(decoded_token.get("iat"))
        ).in_words() == "1 hour"
        user_repository.get_by_email.assert_called_once_with(user.email)

    async def test_fail_to_login_due_user_not_found_by_email(
        self,
        mocker,
        auth_service: AuthService,
        user: User,
        user_repository: UserRepository,
    ):
        error_message = "The requested user was not found"
        mocker.patch.object(UserRepository, "get_by_email", return_value=None)

        with pytest.raises(UserNotFoundException) as excinfo:
            await auth_service.login(user.email, self.PASSWORD)

        assert status.HTTP_404_NOT_FOUND == excinfo.value.status_code
        assert error_message == excinfo.value.detail
        user_repository.get_by_email.assert_called_once_with(user.email)

    async def test_fail_to_login_due_password_does_not_match(
        self,
        mocker,
        auth_service: AuthService,
        password_hasher: PasswordHasher,
        user: User,
        user_repository: UserRepository,
    ):
        mocker.patch.object(UserRepository, "get_by_email", return_value=user)

        with pytest.raises(HTTPException) as excinfo:
            await auth_service.login(
                user.email, password_hasher.hash("doest_not_match")
            )

        assert status.HTTP_401_UNAUTHORIZED == excinfo.value.status_code
        assert "Unauthorized" == excinfo.value.detail
        user_repository.get_by_email.assert_called_once_with(user.email)

    async def test_successfully_logout(
        self,
        mocker,
        auth_service: AuthService,
        cache_service: CacheService,
        jwt_token: JWTToken,
    ):
        mocker.patch.object(CacheService, "put", return_value=True)

        await auth_service.logout(jwt_token)

        cache_service.put.assert_called_once_with(
            f"jti_{jwt_token.jti}", jwt_token.model_dump(), jwt_token.exp
        )

    async def test_fail_to_logout_due_to_cache_service_exception(
        self,
        mocker,
        auth_service: AuthService,
        cache_service: CacheService,
        jwt_token: JWTToken,
    ):
        mocker.patch.object(
            CacheService,
            "put",
            side_effect=CacheServiceException("Internal Server Error"),
        )

        with pytest.raises(CacheServiceException) as excinfo:
            await auth_service.logout(jwt_token)

        assert status.HTTP_500_INTERNAL_SERVER_ERROR == excinfo.value.status_code
        assert "Internal Server Error" == excinfo.value.detail
        cache_service.put.assert_called_once_with(
            f"jti_{jwt_token.jti}", jwt_token.model_dump(), jwt_token.exp
        )
