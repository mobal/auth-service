from typing import Any

import pendulum
from aws_lambda_powertools import Logger
from starlette import status

from app.exceptions import TokenNotFoundException
from app.models.jwt import JWTToken, RefreshToken
from app.repositories.token_repository import TokenRepository

ERROR_MESSAGE_TOKEN_NOT_FOUND = "The requested token was not found"


class TokenService:
    def __init__(self):
        self._logger = Logger()
        self._token_repository = TokenRepository()

    def create(self, jwt_token: JWTToken, refresh_token: RefreshToken | None):
        self._logger.info(
            f"Creating token record for jti={jwt_token.jti}",
            extra={"has_refresh_token": refresh_token is not None},
        )
        token_data = {
            "jti": jwt_token.jti,
            "jwt_token": jwt_token.model_dump(),
            "created_at": pendulum.from_timestamp(jwt_token.iat).to_iso8601_string(),
            "expire_at": pendulum.from_timestamp(
                refresh_token.ttl if refresh_token else jwt_token.exp
            ).to_iso8601_string(),
            "ttl": refresh_token.ttl if refresh_token else jwt_token.exp,
        }

        if refresh_token:
            token_data["refresh_token"] = refresh_token.token

        self._token_repository.create_token(token_data)

    def delete_by_id(self, jti: str):
        self._logger.info(f"Deleting token record for jti={jti}")
        response = self._token_repository.delete_by_id(jti)
        if response["ResponseMetadata"]["HTTPStatusCode"] != status.HTTP_200_OK:
            self._logger.warning(f"Token delete failed for jti={jti}")
            raise TokenNotFoundException(ERROR_MESSAGE_TOKEN_NOT_FOUND)

    def get_by_id(self, jti: str) -> tuple[JWTToken, str] | None:
        self._logger.debug(f"Fetching token record by jti={jti}")
        return self._token_repository.get_by_id(jti)

    def get_by_refresh_token(self, refresh_token: str) -> dict[str, Any] | None:
        self._logger.debug("Fetching token record by refresh token")
        return self._token_repository.get_by_refresh_token(refresh_token)
