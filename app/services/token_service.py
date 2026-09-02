from datetime import UTC, datetime

from aws_lambda_powertools import Logger

from app.exceptions import TokenNotFoundException
from app.models.jwt import JWTToken, RefreshToken
from app.repositories.token_repository import TokenRepository

ERROR_MESSAGE_TOKEN_NOT_FOUND = "The requested token was not found"


class TokenService:
    def __init__(self, token_repository: TokenRepository):
        self._logger = Logger()
        self._token_repository = token_repository

    def create(self, jwt_token: JWTToken, refresh_token: RefreshToken | None) -> None:
        self._logger.info(
            "Creating token record for jti=%s",
            jwt_token.jti,
            extra={"has_refresh_token": refresh_token is not None},
        )
        token_data = {
            "jti": jwt_token.jti,
            "jwt_token": jwt_token.model_dump(),
            "created_at": datetime.fromtimestamp(jwt_token.iat, tz=UTC).isoformat(),
            "expire_at": datetime.fromtimestamp(
                refresh_token.ttl if refresh_token else jwt_token.exp, tz=UTC
            ).isoformat(),
            "ttl": refresh_token.ttl if refresh_token else jwt_token.exp,
        }

        if refresh_token:
            token_data["refresh_token"] = refresh_token.token

        self._token_repository.create_token(token_data)

    def delete_by_id(self, jti: str) -> None:
        self._logger.info("Deleting token record for jti=%s", jti)
        result = self._token_repository.delete_by_id(jti)
        if not result:
            self._logger.warning("Token delete failed for jti=%s", jti)
            raise TokenNotFoundException(ERROR_MESSAGE_TOKEN_NOT_FOUND)

    def consume_by_id(self, jti: str) -> bool:
        self._logger.info("Consuming token record for jti=%s", jti)
        return self._token_repository.delete_by_id(jti)

    def get_by_id(self, jti: str) -> tuple[JWTToken, str, int] | None:
        self._logger.debug("Fetching token record by jti=%s", jti)
        item = self._token_repository.get_by_id(jti)
        if item is None:
            return None
        return JWTToken(**item["jwt_token"]), item.get("refresh_token", ""), item["ttl"]

    def get_by_refresh_token(
        self, refresh_token: str
    ) -> tuple[JWTToken, str, int] | None:
        self._logger.debug("Fetching token record by refresh token")
        item = self._token_repository.get_by_refresh_token(refresh_token)
        if item is None:
            return None
        return JWTToken(**item["jwt_token"]), item.get("refresh_token", ""), item["ttl"]
