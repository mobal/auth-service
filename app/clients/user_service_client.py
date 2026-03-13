import httpx
from aws_lambda_powertools import Logger
from starlette import status

from app import settings

logger = Logger()


class UserServiceClient:
    def get_user_by_email(self, email: str, jwt_token: str) -> dict | None:
        logger.info(f"Fetching user from user-service email={email}")
        try:
            response = httpx.get(
                f"{settings.user_service_base_url}/users",
                params={"email": email},
                headers={"Authorization": f"Bearer {jwt_token}"},
            )
        except httpx.HTTPStatusError as err:
            if err.response.status_code == status.HTTP_404_NOT_FOUND:
                logger.warning(f"User with email {email} not found in user-service")
                return None
            raise

        users = response.json()
        if not users:
            return None
        return users[0]

    def get_user_by_id(self, user_id: str, jwt_token: str) -> dict | None:
        logger.info(f"Fetching user from user-service user_id={user_id}")

        try:
            response = httpx.get(
                f"{settings.user_service_base_url}/users/{user_id}",
                headers={"Authorization": f"Bearer {jwt_token}"},
            )
        except httpx.HTTPStatusError as err:
            if err.response.status_code == status.HTTP_404_NOT_FOUND:
                logger.warning(f"User with ID {user_id} not found in user-service")
                return None

            logger.error(f"Error fetching user by ID: {err}")
            raise

        return response.json()
