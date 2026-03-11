import uuid
from typing import Any

import httpx
import jwt
import pendulum
from aws_lambda_powertools import Logger
from starlette import status

from app import settings

logger = Logger()

SERVICE_TOKEN_LIFETIME = 30


class UserServiceClient:
    def __init__(self):
        self._jwt_token: str | None = None
        self._jwt_token_expires_at: int = 0

    def _generate_jwt_token(self) -> dict[str, Any]:
        iat = pendulum.now()
        exp = iat.add(seconds=settings.jwt_token_lifetime)
        payload = {
            "exp": exp.int_timestamp,
            "iat": iat.int_timestamp,
            "jti": str(uuid.uuid4()),
            "sub": settings.user_service_client_id,
        }

        if settings.jwt_issuer:
            payload["iss"] = settings.jwt_issuer

        return payload

    def _get_access_token(self) -> str:
        now = pendulum.now().int_timestamp
        if (
            self._jwt_token
            and now < self._jwt_token_expires_at - SERVICE_TOKEN_LIFETIME
        ):
            return self._jwt_token

        payload = self._generate_jwt_token()
        self._jwt_token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
        self._jwt_token_expires_at = payload["exp"]

        logger.info("Generated new service-to-service access token")
        return self._jwt_token

    def _get_auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._get_access_token()}"}

    def get_user_by_email(self, email: str) -> dict | None:
        logger.info(f"Fetching user from user-service email={email}")
        try:
            response = httpx.get(
                f"{settings.user_service_base_url}/users",
                params={"email": email},
                headers=self._get_auth_headers(),
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

    def get_user_by_id(self, user_id: str) -> dict | None:
        logger.info(f"Fetching user from user-service user_id={user_id}")

        try:
            response = httpx.get(
                f"{settings.user_service_base_url}/users/{user_id}",
                headers=self._get_auth_headers(),
            )
        except httpx.HTTPStatusError as err:
            if err.response.status_code == status.HTTP_404_NOT_FOUND:
                logger.warning(f"User with ID {user_id} not found in user-service")
                return None

            logger.error(f"Error fetching user by ID: {err}")
            raise

        return response.json()
