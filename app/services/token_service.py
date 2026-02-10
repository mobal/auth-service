from typing import Any

import pendulum
from starlette import status

from app.exceptions import TokenNotFoundException
from app.models.jwt import JWTToken
from app.repositories.token_repository import TokenRepository

ERROR_MESSAGE_TOKEN_NOT_FOUND = "The requested token was not found"

class TokenService:
    def __init__(self):
        self._token_repository = TokenRepository()

    def create(self, jwt_token: JWTToken, refresh_token: str):
        now = pendulum.now()
        self._token_repository.create_token(
            {
                "jti": jwt_token.jti,
                "jwt_token": jwt_token.model_dump(),
                "refresh_token": refresh_token,
                "created_at": now.to_iso8601_string(),
                "ttl": jwt_token.exp,
            }
        )

    def delete_by_id(self, jti: str):
        response = self._token_repository.delete_by_id(jti)
        if response["ResponseMetadata"]["HTTPStatusCode"] != status.HTTP_200_OK:
            raise TokenNotFoundException(ERROR_MESSAGE_TOKEN_NOT_FOUND)

    def get_by_id(self, jti: str) -> tuple[JWTToken, str] | None:
        return self._token_repository.get_by_id(jti)

    def get_by_refresh_token(self, refresh_token: str) -> dict[str, Any] | None:
        return self._token_repository.get_by_refresh_token(refresh_token)
