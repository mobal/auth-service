import uuid

import pytest
from fastapi import status

from app.exceptions import UserAlreadyExistsException
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService


class TestUserService:
    @pytest.fixture
    def user_service(self) -> UserService:
        return UserService()

    def test_successfully_register_user(
        self,
        mocker,
        user: User,
        user_repository: UserRepository,
        user_service: UserService,
    ):
        mocker.patch.object(UserRepository, "get_by_email", return_value=None)
        mocker.patch.object(UserRepository, "create_user")

        user_id = user_service.register(
            user.email, user.password, user.username, user.display_name
        )

        assert isinstance(user_id, str)
        assert uuid.UUID(user_id)
        user_repository.get_by_email.assert_called_once_with(user.email)
        user_repository.create_user.assert_called_once()

    def test_successfully_register_user_without_display_name(
        self,
        mocker,
        user: User,
        user_repository: UserRepository,
        user_service: UserService,
    ):
        mocker.patch.object(UserRepository, "get_by_email", return_value=None)
        mocker.patch.object(UserRepository, "create_user")

        user_id = user_service.register(user.email, user.password, user.username, "")

        assert isinstance(user_id, str)
        assert uuid.UUID(user_id)
        user_repository.get_by_email.assert_called_once_with(user.email)
        user_repository.create_user.assert_called_once()

        call_args = user_repository.create_user.call_args[0][0]
        assert call_args["display_name"] == user.username

    def test_fail_to_register_user_due_to_user_already_exists(
        self,
        mocker,
        user: User,
        user_repository: UserRepository,
        user_service: UserService,
    ):
        error_message = f"User with email {user.email} already exists"
        mocker.patch.object(UserRepository, "get_by_email", return_value=user)

        with pytest.raises(UserAlreadyExistsException) as excinfo:
            user_service.register(
                user.email, user.password, user.username, user.display_name
            )

        assert status.HTTP_409_CONFLICT == excinfo.value.status_code
        assert error_message == excinfo.value.detail
        user_repository.get_by_email.assert_called_once_with(user.email)
