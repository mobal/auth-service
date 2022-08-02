import uuid

import pendulum
import pytest
from botocore.exceptions import ClientError
from starlette import status
from starlette.testclient import TestClient

from app.models import JWTToken, User
from app.services import AuthService


@pytest.mark.asyncio
class TestApp:
    BASE_URL = '/api/v1'

    @pytest.fixture
    def auth_service(self) -> AuthService:
        return AuthService()

    @pytest.fixture
    def authenticated_test_client(self, jwt_token, test_client) -> TestClient:
        from app.main import jwt_bearer
        jwt_bearer.decoded_token = jwt_token
        test_client.app.dependency_overrides[jwt_bearer] = lambda: jwt_token
        return test_client

    @pytest.fixture
    def credentials_dict(self) -> dict:
        return {'email': 'root@netcode.hu', 'password': 'root'}

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
    def test_client(self) -> TestClient:
        from app.main import app
        return TestClient(app, raise_server_exceptions=False)

    @pytest.fixture
    def user(self) -> User:
        return User(
            id=str(uuid.uuid4()),
            display_name='root',
            email='root@netcode.hu',
            password='password',
            roles=['root'],
            username='root',
            created_at=pendulum.now().to_iso8601_string()
        )

    async def test_successfully_login(self, mocker, auth_service, credentials_dict, test_client):
        mocker.patch('app.services.AuthService.login', return_value=None)
        response = test_client.post(
            f'{self.BASE_URL}/login',
            json=credentials_dict)
        assert status.HTTP_200_OK == response.status_code
        auth_service.login.assert_called_once_with(
            credentials_dict['email'], credentials_dict['password'])

    async def test_fail_to_login_due_empty_body(self, test_client):
        response = test_client.post(f'{self.BASE_URL}/login', json=None)
        assert status.HTTP_400_BAD_REQUEST == response.status_code

    async def test_fail_to_login_due_invalid_credentials(self, test_client):
        login_url = f'{self.BASE_URL}/login'
        response = test_client.post(
            login_url, json={
                'email': '', 'password': ''})
        assert status.HTTP_400_BAD_REQUEST == response.status_code, 'empty email and password'
        response = test_client.post(
            login_url, json={
                'email': 'asd', 'password': 'as'})
        assert status.HTTP_400_BAD_REQUEST == response.status_code, 'invalid email and password'
        response = test_client.post(
            login_url, json={
                'email': 'asd', 'password': 'root'})
        assert status.HTTP_400_BAD_REQUEST == response.status_code, 'invalid email'
        response = test_client.post(
            login_url,
            json={
                'email': 'root@netcode.hu',
                'password': ''})
        assert status.HTTP_400_BAD_REQUEST == response.status_code, 'empty password'
        response = test_client.post(
            login_url,
            json={
                'email': 'root@netcode.hu',
                'password': 'as'})
        assert status.HTTP_400_BAD_REQUEST == response.status_code, 'invalid password password length'

    async def test_fail_to_login_due_client_error(self, mocker, auth_service, credentials_dict, test_client):
        mocker.patch(
            'app.services.AuthService.login',
            side_effect=ClientError(
                error_response={},
                operation_name='testing'))
        response = test_client.post(
            f'{self.BASE_URL}/login',
            json=credentials_dict)
        assert status.HTTP_500_INTERNAL_SERVER_ERROR == response.status_code
        auth_service.login.assert_called_once_with(
            credentials_dict['email'], credentials_dict['password'])

    async def test_successfully_logout(self, mocker, authenticated_test_client, cache_service, jwt_token):
        mocker.patch('app.services.CacheService.put', return_value=True)
        response = authenticated_test_client.get(f'{self.BASE_URL}/logout')
        assert status.HTTP_204_NO_CONTENT == response.status_code
        cache_service.put.assert_called_once_with(
            f'jti_{jwt_token.jti}', jwt_token.dict(), jwt_token.exp)

    async def test_fail_to_logout(self, mocker, authenticated_test_client, cache_service, jwt_token):
        mocker.patch('app.services.CacheService.put', return_value=False)
        response = authenticated_test_client.get(f'{self.BASE_URL}/logout')
        assert status.HTTP_500_INTERNAL_SERVER_ERROR == response.status_code
        cache_service.put.assert_called_once_with(
            f'jti_{jwt_token.jti}', jwt_token.dict(), jwt_token.exp)
