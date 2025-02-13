import uuid

import pytest

from app.models import User
from app.repositories import UserRepository


@pytest.mark.asyncio
class TestUserRepository:
    async def test_successfully_get_by_email(
        self, users_table, user_model: User, user_repository: UserRepository
    ):
        item = await user_repository.get_by_email(user_model.email)

        assert user_model == item

    async def test_successfully_return_none_by_email(
        self, users_table, user_repository: UserRepository
    ):
        item = await user_repository.get_by_email("hello@netcode.hu")

        assert item is None

    async def test_successfully_get_by_id(
        self, users_table, user_model: User, user_repository: UserRepository
    ):
        item = await user_repository.get_by_id(user_model.id)

        assert user_model == item

    async def test_successfully_return_none_by_id(
        self, users_table, user_repository: UserRepository
    ):
        item = await user_repository.get_by_id(str(uuid.uuid4()))

        assert item is None
