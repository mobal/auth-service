import secrets

import pendulum
from aws_lambda_powertools import Logger

from app import settings
from app.models.authorization_code import AuthorizationCode


class AuthorizationCodeRepository:
    def __init__(self):
        self._logger = Logger()
        self._dynamodb = __import__("boto3").resource("dynamodb")
        self._table = self._dynamodb.Table(f"{settings.stage}-authorization_codes")

    def create(
        self,
        client_id: str,
        user_id: str,
        redirect_uri: str,
        scope: str | None = None,
        code_challenge: str | None = None,
        code_challenge_method: str | None = None,
    ) -> str:
        """Create and store authorization code."""
        code = secrets.token_urlsafe(32)
        now = pendulum.now()
        ttl = (now.add(minutes=10)).int_timestamp

        self._table.put_item(
            Item={
                "code": code,
                "client_id": client_id,
                "user_id": user_id,
                "redirect_uri": redirect_uri,
                "scope": scope,
                "code_challenge": code_challenge,
                "code_challenge_method": code_challenge_method,
                "created_at": now.to_iso8601_string(),
                "expire_at": pendulum.from_timestamp(ttl).to_iso8601_string(),
                "ttl": ttl,
            }
        )

        self._logger.info(
            f"Created authorization code for client={client_id}, user={user_id}"
        )
        return code

    def get_by_code(self, code: str) -> AuthorizationCode | None:
        """Retrieve authorization code by code."""
        response = self._table.get_item(Key={"code": code})

        if "Item" not in response:
            return None

        item = response["Item"]
        return AuthorizationCode(
            code=item["code"],
            client_id=item["client_id"],
            user_id=item["user_id"],
            redirect_uri=item["redirect_uri"],
            scope=item.get("scope"),
            code_challenge=item.get("code_challenge"),
            code_challenge_method=item.get("code_challenge_method"),
            ttl=item["ttl"],
        )

    def delete_by_code(self, code: str) -> None:
        """Delete authorization code (one-time use)."""
        self._table.delete_item(Key={"code": code})
        self._logger.info(f"Deleted authorization code {code}")
