import httpx2 as httpx
from aws_lambda_powertools import Logger
from starlette import status

from app import settings
from app.clients.circuit_breaker import create_circuit_breaker

logger = Logger()


class UserServiceClient:
    def __init__(self) -> None:
        self._client = httpx.Client(timeout=httpx.Timeout(10.0))
        self._breaker = create_circuit_breaker("user-service")

    def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make a request and count transport and upstream-server failures."""
        if method == "GET":
            response = self._client.get(url, **kwargs)
        elif method == "POST":
            response = self._client.post(url, **kwargs)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        if response.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
            response.raise_for_status()
        return response

    def get_user_by_email(self, email: str, jwt_token: str) -> dict | None:
        logger.info("Fetching user from user-service by email")
        try:
            response = self._breaker.call(
                self._request,
                "GET",
                f"{settings.user_service_base_url}/api/v1/users",
                params={"email": email},
                headers={"Authorization": f"Bearer {jwt_token}"},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as err:
            if err.response.status_code == status.HTTP_404_NOT_FOUND:
                logger.warning("User with email %s not found in user-service", email)
                return None
            logger.error("Error fetching user by email: %s", err)
            raise
        except httpx.RequestError as err:
            logger.error("Connection error fetching user by email: %s", err)
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

        try:
            response = self._breaker.call(
                self._request,
                "POST",
                f"{settings.user_service_base_url}/api/v1/users/{user_id}/validate",
                json={"password": password},
                headers={"Authorization": f"Bearer {jwt_token}"},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as err:
            if err.response.status_code in (
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_CONTENT,
            ):
                logger.warning(
                    "Password validation failed user_id=%s",
                    user_id,
                    extra={"status_code": err.response.status_code},
                )
                return False
            logger.error(
                "Unexpected error validating password user_id=%s",
                user_id,
                extra={"status_code": err.response.status_code},
            )
            raise
        except httpx.RequestError:
            logger.error("Connection error validating password user_id=%s", user_id)
            raise

        logger.info("Password validated for user_id=%s", user_id)
        return True

    def get_user_by_id(self, user_id: str, jwt_token: str) -> dict | None:
        logger.info("Fetching user from user-service user_id=%s", user_id)

        try:
            response = self._breaker.call(
                self._request,
                "GET",
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
        except httpx.RequestError as err:
            logger.error("Connection error fetching user by ID: %s", err)
            raise

        result = response.json()
        logger.info("User fetched from user-service user_id=%s", user_id)
        return result
