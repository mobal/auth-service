from typing import Any

import pendulum
from starlette import status

from app.exceptions import TokenNotFoundException
from app.models.jwt import JWTToken, RefreshToken
from app.repositories.token_repository import TokenRepository

ERROR_MESSAGE_TOKEN_NOT_FOUND = "The requested token was not found"


class TokenService:
    def __init__(self):
        self._token_repository = TokenRepository()

    def create(self, jwt_token: JWTToken, refresh_token: RefreshToken):
        self._token_repository.create_token(
            {
                "jti": jwt_token.jti,
                "jwt_token": jwt_token.model_dump(),
                "refresh_token": refresh_token.token,
                "created_at": pendulum.now().to_iso8601_string(),
                "refresh_token_ttl": refresh_token.ttl,
                "ttl": refresh_token.ttl,
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
