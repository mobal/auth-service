import uuid

import pendulum

from app.models.user import User
from app.repositories.user_repository import UserRepository


class TestUserRepository:
    def test_successfully_create_user(
        self, user: User, user_repository: UserRepository, users_table
    ):
        new_user_id = str(uuid.uuid4())
        user_data = {
            "id": new_user_id,
            "display_name": "new_user",
            "email": "newuser@netcode.hu",
            "password": "hashed_password",
            "username": "newuser",
            "created_at": pendulum.now().to_iso8601_string(),
        }
        user_repository.create_user(user_data)

        response = users_table.get_item(Key={"id": new_user_id})

        assert response["Item"] == user_data

    def test_successfully_delete_user(
        self, user: User, user_repository: UserRepository, users_table
    ):
        response = user_repository.delete_user(user.id)

        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    def test_delete_user_returns_empty_attributes_if_id_not_found(
        self, user_repository: UserRepository, users_table
    ):
        response = user_repository.delete_user(str(uuid.uuid4()))

        assert response["Attributes"] == {}

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

    def test_successfully_get_by_username(
        self, users_table, user: User, user_repository: UserRepository
    ):
        item = user_repository.get_by_username(user.username)

        assert user == item

    def test_successfully_return_none_by_username(
        self, users_table, user_repository: UserRepository
    ):
        item = user_repository.get_by_username("nonexistentuser")

        assert item is None
