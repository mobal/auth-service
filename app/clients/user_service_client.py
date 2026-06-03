import httpx
from aws_lambda_powertools import Logger
from starlette import status

from app import settings

logger = Logger()


class UserServiceClient:
    def get_user_by_email(self, email: str, jwt_token: str) -> dict | None:
        logger.info("Fetching user from user-service by email")
        try:
            response = httpx.get(
                f"{settings.user_service_base_url}/api/v1/users",
                params={"email": email},
                headers={"Authorization": f"Bearer {jwt_token}"},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as err:
            if err.response.status_code == status.HTTP_404_NOT_FOUND:
                logger.warning("User with email %s not found in user-service", email)
                return None
            raise

        result = response.json()
        if not result or "items" not in result or not result["items"]:
            logger.warning("User-service returned no user for requested email")
            return None
        logger.info("User fetched from user-service by email")
        return result["items"][0]

    def validate_user_password(
        self, user_id: str, password: str, jwt_token: str
    ) -> bool:
        logger.info("Validating user password user_id=%s", user_id)

        response = httpx.post(
            f"{settings.user_service_base_url}/api/v1/users/{user_id}/validate",
            json={"password": password},
            headers={"Authorization": f"Bearer {jwt_token}"},
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as err:
            if 400 <= err.response.status_code < 500:
                logger.warning(
                    "Password validation failed user_id=%s",
                    user_id,
                    extra={"status_code": err.response.status_code},
                )
                return False
            raise

        logger.info("Password validated for user_id=%s", user_id)
        return True

    def get_user_by_id(self, user_id: str, jwt_token: str) -> dict | None:
        logger.info("Fetching user from user-service user_id=%s", user_id)

        try:
            response = httpx.get(
                f"{settings.user_service_base_url}/api/v1/users/{user_id}",
                headers={"Authorization": f"Bearer {jwt_token}"},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as err:
            if err.response.status_code == status.HTTP_404_NOT_FOUND:
                logger.warning("User with ID %s not found in user-service", user_id)
                return None

            logger.error("Error fetching user by ID: %s", err)
            raise

        logger.info("User fetched from user-service user_id=%s", user_id)
        return response.json()
