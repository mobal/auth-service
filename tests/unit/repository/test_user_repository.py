import uuid

from app.models.user import User
from app.repositories.user_repository import UserRepository


class TestUserRepository:
    def test_successfully_get_by_email(
        self, users_table, user: User, user_repository: UserRepository
    ):
        item = user_repository.get_by_email(user.email)

        assert user == item

    def test_successfully_return_none_by_email(
        self, users_table, user_repository: UserRepository
    ):
        item = user_repository.get_by_email("hello@netcode.hu")

        assert item is None

    def test_successfully_get_by_id(
        self, users_table, user: User, user_repository: UserRepository
    ):
        item = user_repository.get_by_id(user.id)

        assert user == item

    def test_successfully_return_none_by_id(
        self, users_table, user_repository: UserRepository
    ):
        item = user_repository.get_by_id(str(uuid.uuid4()))

        assert item is None
