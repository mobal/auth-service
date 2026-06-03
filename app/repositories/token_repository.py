from typing import Any

import boto3
from aws_lambda_powertools import Logger
from boto3.dynamodb.conditions import Key

from app import settings


class TokenRepository:
    def __init__(self):
        self._logger = Logger()
        self._table = (
            boto3.Session().resource("dynamodb").Table(f"{settings.stage}-tokens")
        )

    def create_token(self, data: dict[str, Any]) -> dict[str, Any]:
        self._logger.debug(f"Persisting token record jti={data.get('jti')}")
        return self._table.put_item(Item=data)

    def delete_by_id(self, jti: str) -> dict[str, Any]:
        self._logger.debug(f"Deleting token record jti={jti}")
        return self._table.delete_item(Key={"jti": jti})

    def consume_by_id(self, jti: str) -> bool:
        self._logger.debug(f"Consuming token record jti={jti}")
        response = self._table.delete_item(
            Key={"jti": jti},
            ReturnValues="ALL_OLD",
        )
        return "Attributes" in response

    def get_by_id(self, jti: str) -> dict[str, Any] | None:
        self._logger.debug(f"Querying token record by jti={jti}")
        response = self._table.get_item(
            Key={"jti": jti},
        )
        if "Item" in response:
            return response["Item"]
        self._logger.debug(f"Token record not found for jti={jti}")
        return None

    def get_by_refresh_token(self, refresh_token: str) -> dict[str, Any] | None:
        self._logger.debug("Querying token record by refresh token")
        response = self._table.query(
            IndexName="RefreshTokenIndex",
            KeyConditionExpression=Key("refresh_token").eq(refresh_token),
        )
        if not response["Items"]:
            self._logger.debug("Token record not found for refresh token")
            return None
        return response["Items"][0]
