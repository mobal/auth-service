import pybreaker
import pytest

from app import settings
from app.clients.user_service_client import UserServiceClient
from app.dependencies import get_user_service_client


@pytest.fixture(autouse=True)
def clear_user_service_client_cache():
    get_user_service_client.cache_clear()
    yield
    get_user_service_client.cache_clear()


class TestCircuitBreaker:
    def test_production_user_service_dependency_reuses_breaker(
        self,
        httpx2_mock,
    ):
        client = get_user_service_client()
        assert isinstance(client, UserServiceClient)
        assert get_user_service_client() is client

        client._breaker = pybreaker.CircuitBreaker(fail_max=1, reset_timeout=60)
        url = (
            f"{settings.user_service_base_url}/api/v1/users?email=breaker%40example.com"
        )
        httpx2_mock.add_response(method="GET", url=url, status_code=503)

        with pytest.raises(pybreaker.CircuitBreakerError):
            client.get_user_by_email("breaker@example.com", "service-token")

        with pytest.raises(pybreaker.CircuitBreakerError):
            client.get_user_by_email("breaker@example.com", "service-token")

        assert len(httpx2_mock.get_requests()) == 1
