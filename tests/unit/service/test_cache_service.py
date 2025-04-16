import uuid

import pendulum
import pytest
from fastapi import status
from httpx import Response
from respx import MockRouter

from app.exceptions import CacheServiceException
from app.middlewares import correlation_id
from app.services import CacheService
from app.settings import Settings


@pytest.mark.asyncio
class TestCacheService:
    key_value = {
        "key": str(uuid.uuid4()),
        "value": "Some random value",
        "created_at": pendulum.now().to_iso8601_string(),
        "ttl": pendulum.now().int_timestamp,
    }

    @pytest.fixture(autouse=True)
    def setup_function(self):
        correlation_id.set(str(uuid.uuid4()))

    async def test_successfully_get_key_value(
        self,
        cache_service: CacheService,
        settings: Settings,
        respx_mock: MockRouter,
    ):
        route = respx_mock.get(
            f'{settings.cache_service_base_url}/api/cache/{self.key_value["key"]}'
        ).mock(
            return_value=Response(status_code=status.HTTP_200_OK, json=self.key_value)
        )

        assert await cache_service.get(self.key_value["key"]) is True

        assert 1 == route.call_count

    async def test_successfully_put_key_value(
        self, cache_service: CacheService, settings: Settings, respx_mock: MockRouter
    ):
        route = respx_mock.post(f"{settings.cache_service_base_url}/api/cache").mock(
            Response(status_code=status.HTTP_201_CREATED)
        )

        await cache_service.put(
            self.key_value["key"], self.key_value["value"], pendulum.now().int_timestamp
        )

        assert 1 == route.call_count

    async def test_fail_to_put_key_value_due_empty_values(
        self, cache_service: CacheService, settings: Settings, respx_mock: MockRouter
    ):
        route = respx_mock.post(f"{settings.cache_service_base_url}/api/cache").mock(
            Response(status_code=status.HTTP_400_BAD_REQUEST)
        )

        with pytest.raises(CacheServiceException) as excinfo:
            await cache_service.put("", "")

        assert CacheServiceException.__name__ == excinfo.typename
        assert status.HTTP_500_INTERNAL_SERVER_ERROR == excinfo.value.status_code
        assert "Internal Server Error" == excinfo.value.detail
        assert 1 == route.call_count

    async def test_fail_to_get_key_value_due_invalid_id(
        self, cache_service: CacheService, settings: Settings, respx_mock: MockRouter
    ):
        message = f'The requested value was not found for key={self.key_value["key"]}'
        route = respx_mock.get(
            f'{settings.cache_service_base_url}/api/cache/{self.key_value["key"]}'
        ).mock(
            Response(
                status_code=status.HTTP_404_NOT_FOUND,
                json={
                    "status": status.HTTP_404_NOT_FOUND,
                    "id": self.key_value["key"],
                    "message": message,
                },
            ),
        )

        assert await cache_service.get(self.key_value["key"]) is False

        assert 1 == route.call_count

    async def test_fail_to_get_key_value_due_unexpected_return_value(
        self, cache_service: CacheService, settings: Settings, respx_mock: MockRouter
    ):
        route = respx_mock.get(
            f'{settings.cache_service_base_url}/api/cache/{self.key_value["key"]}'
        ).mock(
            Response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        )

        with pytest.raises(CacheServiceException) as excinfo:
            await cache_service.get(self.key_value["key"])

        assert CacheServiceException.__name__ == excinfo.typename
        assert status.HTTP_500_INTERNAL_SERVER_ERROR == excinfo.value.status_code
        assert 1 == route.call_count
