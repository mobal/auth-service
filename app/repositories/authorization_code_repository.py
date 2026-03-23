import secrets
import uuid

import pendulum
from aws_lambda_powertools import Logger
from boto3.dynamodb.conditions import Key

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
        code = secrets.token_urlsafe(32)
        now = pendulum.now()
        ttl = (now.add(minutes=10)).int_timestamp

        self._table.put_item(
            Item={
                "id": str(uuid.uuid4()),
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

    def delete_by_id(self, code_id: str) -> None:
        self._table.delete_item(Key={"id": code_id})
        self._logger.info(f"Deleted authorization code {code_id}")

    def get_by_code(self, code: str) -> AuthorizationCode | None:
        self._logger.debug("Querying authorization code by code value")
        response = self._table.query(
            IndexName="CodeIndex",
            KeyConditionExpression=Key("code").eq(code),
        )

        if "Items" not in response or not response["Items"]:
            self._logger.warning("Authorization code not found")
            return None

        item = response["Items"][0]
        self._logger.info(
            f"Authorization code found id={item['id']}",
            extra={"client_id": item["client_id"], "user_id": item["user_id"]},
        )
        return AuthorizationCode(
            id=item["id"],
            code=item["code"],
            client_id=item["client_id"],
            user_id=item["user_id"],
            redirect_uri=item["redirect_uri"],
            scope=item.get("scope"),
            code_challenge=item.get("code_challenge"),
            code_challenge_method=item.get("code_challenge_method"),
            ttl=item["ttl"],
        )
