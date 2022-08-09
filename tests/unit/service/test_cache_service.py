import uuid
import pendulum
import pytest
from starlette import status


@pytest.mark.asyncio
class TestCacheService:
    @pytest.fixture
    def key_value(self) -> dict:
        now = pendulum.now()
        return {
            'key': str(uuid.uuid4()),
            'value': 'Some random value',
            'created_at': now.to_iso8601_string(),
            'ttl': now.int_timestamp,
        }

    async def test_successfully_get_key_value(
        self, cache_service, key_value, settings, httpx_mock
    ):
        httpx_mock.add_response(
            url=f'{settings.cache_service_base_url}/api/cache/{key_value["key"]}',
            status_code=status.HTTP_200_OK,
            json=key_value,
        )
        result = await cache_service.get(key_value['key'])
        assert bool(result) is True
        assert key_value['key'] == result.key
        assert key_value['created_at'] == result.created_at
        assert key_value['value'] == result.value
        assert key_value['ttl'] == result.ttl

    async def test_successfully_put_key_value(
        self, cache_service, key_value, settings, httpx_mock
    ):
        httpx_mock.add_response(
            url=f'{settings.cache_service_base_url}/api/cache',
            status_code=status.HTTP_201_CREATED,
            method='POST',
        )
        result = await cache_service.put(
            key_value['key'], key_value['value'], pendulum.now().int_timestamp
        )
        assert bool(result) is True

    async def test_fail_to_put_key_value_due_empty_values(
        self, cache_service, key_value, settings, httpx_mock
    ):
        httpx_mock.add_response(
            url=f'{settings.cache_service_base_url}/api/cache',
            status_code=status.HTTP_400_BAD_REQUEST,
            method='POST',
        )
        result = await cache_service.put('', '')
        assert bool(result) is False

    async def test_fail_to_get_key_value_due_invalid_id(
        self, cache_service, key_value, settings, httpx_mock
    ):
        message = f'The requested value was not found for key={key_value["key"]}'
        httpx_mock.add_response(
            url=f'{settings.cache_service_base_url}/api/cache/{key_value["key"]}',
            status_code=status.HTTP_404_NOT_FOUND,
            json={
                'status': status.HTTP_404_NOT_FOUND,
                'id': key_value['key'],
                'message': message,
            },
        )
        result = await cache_service.get(key_value['key'])
        assert result is None
