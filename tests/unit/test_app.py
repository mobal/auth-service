import pytest
from botocore.exceptions import ClientError
from starlette import status
from starlette.testclient import TestClient

from app.exceptions import CacheServiceException
from app.services import AuthService, JWTToken


@pytest.mark.asyncio
class TestApp:
    BASE_URL = '/api/v1'
    X_CORRELATION_ID = 'X-Correlation-ID'

    credentials = {'email': 'root@netcode.hu', 'password': '123456'}

    @pytest.fixture
    def auth_service(self) -> AuthService:
        return AuthService()

    @pytest.fixture
    def test_client_ex(
        self, jwt_token: JWTToken, test_client: TestClient
    ) -> TestClient:
        from app.main import jwt_bearer

        jwt_bearer.decoded_token = jwt_token
        test_client.app.dependency_overrides[jwt_bearer] = lambda: jwt_token
        return test_client

    @pytest.fixture
    def test_client(self) -> TestClient:
        from app.main import app

        return TestClient(app, raise_server_exceptions=False)

    async def test_successfully_login(
        self,
        mocker,
        auth_service: AuthService,
        jwt_token: JWTToken,
        test_client: TestClient,
    ):
        mocker.patch('app.services.AuthService.login', return_value=jwt_token)
        response = test_client.post(f'{self.BASE_URL}/login', json=self.credentials)
        assert status.HTTP_200_OK == response.status_code
        assert self.X_CORRELATION_ID in response.headers
        auth_service.login.assert_called_once_with(
            self.credentials['email'], self.credentials['password']
        )

    async def test_fail_to_login_due_empty_body(self, test_client: TestClient):
        response = test_client.post(f'{self.BASE_URL}/login', json=None)
        assert status.HTTP_400_BAD_REQUEST == response.status_code
        assert self.X_CORRELATION_ID in response.headers

    async def test_fail_to_login_due_invalid_credentials(self, test_client: TestClient):
        login_url = f'{self.BASE_URL}/login'
        response = test_client.post(login_url, json={'email': '', 'password': ''})
        assert (
            status.HTTP_400_BAD_REQUEST == response.status_code
        ), 'empty email and password'
        assert self.X_CORRELATION_ID in response.headers

        response = test_client.post(login_url, json={'email': 'asd', 'password': 'as'})
        assert (
            status.HTTP_400_BAD_REQUEST == response.status_code
        ), 'invalid email and password'
        assert self.X_CORRELATION_ID in response.headers

        response = test_client.post(
            login_url, json={'email': 'asd', 'password': 'root'}
        )
        assert status.HTTP_400_BAD_REQUEST == response.status_code, 'invalid email'
        assert self.X_CORRELATION_ID in response.headers

        response = test_client.post(
            login_url, json={'email': 'root@netcode.hu', 'password': ''}
        )
        assert status.HTTP_400_BAD_REQUEST == response.status_code, 'empty password'
        assert self.X_CORRELATION_ID in response.headers

        response = test_client.post(
            login_url, json={'email': 'root@netcode.hu', 'password': 'as'}
        )
        assert (
            status.HTTP_400_BAD_REQUEST == response.status_code
        ), 'invalid password password length'
        assert self.X_CORRELATION_ID in response.headers

    async def test_fail_to_login_due_client_error(
        self, mocker, auth_service: AuthService, test_client: TestClient
    ):
        mocker.patch(
            'app.services.AuthService.login',
            side_effect=ClientError(error_response={}, operation_name='testing'),
        )
        response = test_client.post(f'{self.BASE_URL}/login', json=self.credentials)
        assert status.HTTP_500_INTERNAL_SERVER_ERROR == response.status_code
        assert self.X_CORRELATION_ID in response.headers
        auth_service.login.assert_called_once_with(
            self.credentials['email'], self.credentials['password']
        )

    async def test_successfully_logout(
        self,
        mocker,
        auth_service: AuthService,
        jwt_token: JWTToken,
        test_client_ex: TestClient,
    ):
        mocker.patch('app.services.AuthService.logout', return_value=None)
        response = test_client_ex.get(f'{self.BASE_URL}/logout')
        assert status.HTTP_204_NO_CONTENT == response.status_code
        assert self.X_CORRELATION_ID in response.headers
        auth_service.logout.assert_called_once_with(jwt_token)

    async def test_fail_to_logout(
        self,
        mocker,
        auth_service: AuthService,
        jwt_token: JWTToken,
        test_client_ex: TestClient,
    ):
        mocker.patch(
            'app.services.AuthService.logout',
            side_effect=CacheServiceException('Internal Server Error'),
        )
        response = test_client_ex.get(f'{self.BASE_URL}/logout')
        assert status.HTTP_500_INTERNAL_SERVER_ERROR == response.status_code
        assert self.X_CORRELATION_ID in response.headers
        assert 3 == len(response.json())
        auth_service.logout.assert_called_once_with(jwt_token)
