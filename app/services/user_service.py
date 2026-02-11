import uuid

import pendulum
from argon2 import PasswordHasher
from aws_lambda_powertools import Logger

from app.exceptions import UserAlreadyExistsException
from app.models.user import User
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self):
        self._logger = Logger()
        self._password_hasher = PasswordHasher()
        self._user_repository = UserRepository()

    def register(
        self, email: str, password: str, username: str, display_name: str | None
    ) -> str:
        self._logger.info(
            f"Registering user with email: {email}",
            extra={"email": email, "username": username, "display_name": display_name},
        )

        if self._user_repository.get_by_email(email):
            self._logger.warning(
                f"User with email {email} already exists", extra={"email": email}
            )
            raise UserAlreadyExistsException(f"User with email {email} already exists")
        if self._user_repository.get_by_username(username):
            self._logger.warning(
                f"User with username {username} already exists",
                extra={"username": username},
            )
            raise UserAlreadyExistsException(
                f"User with username {username} already exists"
            )

        user = User(
            id=str(uuid.uuid4()),
            display_name=display_name,
            email=email,
            password=self._password_hasher.hash(password),
            username=username,
            created_at=pendulum.now().to_iso8601_string(),
        )

        self._user_repository.create_user(user.model_dump(exclude_none=True))

        return user.id
