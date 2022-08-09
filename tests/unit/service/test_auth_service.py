import uuid
from argon2 import PasswordHasher

import jwt
import pendulum
import pytest as pytest
from fastapi import HTTPException
from starlette import status

from app.models import User, JWTToken
from app.repository import UserRepository
from app.services import AuthService


@pytest.mark.asyncio
class TestAuthService:
    CACHE_SERVICE_PUT = 'app.services.CacheService.put'
    USER_REPOSITORY_GET_BY_EMAIL = 'app.repository.UserRepository.get_by_email'

    _password = 'password'

    @pytest.fixture
    def auth_service(self) -> AuthService:
        return AuthService()

    @pytest.fixture
    def jwt_token(self, user) -> JWTToken:
        iat = pendulum.now()
        exp = iat.add(hours=1)
        return JWTToken(
            exp=exp.int_timestamp,
            iat=iat.int_timestamp,
            jti=str(uuid.uuid4()),
            sub=user
        )

    @pytest.fixture
    def password_hasher(self) -> PasswordHasher:
        return PasswordHasher()

    @pytest.fixture
    def user_repository(self) -> UserRepository:
        return UserRepository()

    @pytest.fixture
    def user(self, password_hasher) -> User:
        return User(
            id=str(
                uuid.uuid4()),
            display_name='root',
            email='root@netcode.hu',
            password=password_hasher.hash(self._password),
            roles=['root'],
            username='root',
            created_at=pendulum.now().to_iso8601_string())

    async def test_successfully_login(self, mocker, auth_service, settings, user, user_repository):
        mocker.patch(
            self.USER_REPOSITORY_GET_BY_EMAIL,
            return_value=user)
        token = await auth_service.login(user.email, self._password)
        decoded_token = jwt.decode(token.token, settings.jwt_secret, ['HS256'])
        user_dict = user.dict()
        del user_dict['password']
        assert user_dict == decoded_token['sub']
        user_repository.get_by_email.assert_called_once_with(user.email)

    async def test_fail_to_login_due_user_not_found_by_email(self, mocker, auth_service, user, user_repository):
        error_message = f'The requested user was not found with email={user.email}'
        mocker.patch(
            self.USER_REPOSITORY_GET_BY_EMAIL,
            side_effect=HTTPException(
                status.HTTP_404_NOT_FOUND,
                error_message))
        with pytest.raises(HTTPException) as excinfo:
            await auth_service.login(user.email, self._password)
        assert status.HTTP_404_NOT_FOUND == excinfo.value.status_code
        assert error_message == excinfo.value.detail
        user_repository.get_by_email.assert_called_once_with(user.email)

    async def test_fail_to_login_due_password_does_not_match(self, mocker, auth_service, password_hasher, user, user_repository):
        mocker.patch(
            self.USER_REPOSITORY_GET_BY_EMAIL,
            return_value=user)
        with pytest.raises(HTTPException) as excinfo:
            await auth_service.login(user.email, password_hasher.hash('doest_not_match'))
        assert status.HTTP_401_UNAUTHORIZED == excinfo.value.status_code
        assert 'Invalid email or password' == excinfo.value.detail
        user_repository.get_by_email.assert_called_once_with(user.email)

    async def test_successfully_logout(self, mocker, auth_service, cache_service, jwt_token):
        mocker.patch(self.CACHE_SERVICE_PUT, return_value=True)
        await auth_service.logout(jwt_token)
        cache_service.put.assert_called_once_with(
            f'jti_{jwt_token.jti}', jwt_token.dict(), jwt_token.exp)

    async def test_fail_to_logout_due_cache_returns_false(self, mocker, auth_service, cache_service, jwt_token):
        mocker.patch(self.CACHE_SERVICE_PUT, return_value=False)
        with pytest.raises(HTTPException) as excinfo:
            await auth_service.logout(jwt_token)
        assert status.HTTP_500_INTERNAL_SERVER_ERROR == excinfo.value.status_code
        assert 'Internal Server Error' == excinfo.value.detail
        cache_service.put.assert_called_once_with(
            f'jti_{jwt_token.jti}', jwt_token.dict(), jwt_token.exp)
