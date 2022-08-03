import uuid

import bcrypt
import jwt
import pendulum
import pytest as pytest
from fastapi import HTTPException
from starlette import status

from app.models import User
from app.repository import UserRepository
from app.services import AuthService


@pytest.mark.asyncio
class TestAuthService:
    _password = 'password'

    @pytest.fixture
    def auth_service(self) -> AuthService:
        return AuthService()

    @pytest.fixture
    def user_repository(self) -> UserRepository:
        return UserRepository()

    @pytest.fixture
    def user(self) -> User:
        return User(
            id=str(
                uuid.uuid4()),
            display_name='root',
            email='root@netcode.hu',
            password=bcrypt.hashpw(
                self._password.encode('utf-8'),
                bcrypt.gensalt()),
            roles=['root'],
            username='root',
            created_at=pendulum.now().to_iso8601_string())

    async def test_successfully_login(self, mocker, auth_service, settings, user, user_repository):
        mocker.patch(
            'app.repository.UserRepository.get_by_email',
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
            'app.repository.UserRepository.get_by_email',
            side_effect=HTTPException(
                status.HTTP_404_NOT_FOUND,
                error_message))
        with pytest.raises(HTTPException) as excinfo:
            await auth_service.login(user.email, self._password)
        assert status.HTTP_404_NOT_FOUND == excinfo.value.status_code
        assert error_message == excinfo.value.detail
        user_repository.get_by_email.assert_called_once_with(user.email)

    async def test_fail_to_login_due_password_does_not_match(self, mocker, auth_service, settings, user,
                                                             user_repository):
        mocker.patch(
            'app.repository.UserRepository.get_by_email',
            return_value=user)
        with pytest.raises(HTTPException) as excinfo:
            await auth_service.login(user.email, 'nVwBdBwWfdnQyOmj')
        assert status.HTTP_401_UNAUTHORIZED == excinfo.value.status_code
        assert 'Invalid email or password' == excinfo.value.detail
        user_repository.get_by_email.assert_called_once_with(user.email)
