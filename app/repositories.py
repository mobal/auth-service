from typing import Any

import boto3
from boto3.dynamodb.conditions import Attr, Key

from app import settings
from app.models import JWTToken, User


class UserRepository:
    def __init__(self):
        self._table = (
            boto3.Session().resource("dynamodb").Table(f"{settings.stage}-users")
        )

    def get_by_email(self, email: str) -> User | None:
        response = self._table.scan(
            FilterExpression=Attr("deleted_at").eq(None) & Attr("email").eq(email)
        )
        if response["Items"]:
            return User(**response["Items"][0])
        return None

    def get_by_id(self, user_uuid: str) -> User | None:  # pragma: no cover
        response = self._table.query(
            KeyConditionExpression=Key("id").eq(user_uuid),
            FilterExpression=Attr("deleted_at").eq(None),
        )
        if response["Items"]:
            return User(**response["Items"][0])
        return None


class TokenRepository:
    def __init__(self):
        self._table = (
            boto3.Session().resource("dynamodb").Table(f"{settings.stage}-tokens")
        )

    def create_token(self, data: dict[str, Any]) -> dict[str, Any]:
        return self._table.put_item(Item=data)

    def delete_by_id(self, jti: str) -> dict[str, Any]:
        return self._table.delete_item(Key={"jti": jti})

    def get_by_id(self, jti: str) -> tuple[JWTToken, str] | None:
        response = self._table.get_item(
            Key={"jti": jti},
        )
        if "Item" in response:
            return (
                JWTToken(**response["Item"]["jwt_token"]),
                response["Item"]["refresh_token"],
            )
        return None

    def get_by_refresh_token(self, refresh_token: str) -> dict[str, Any] | None:
        response = self._table.query(
            IndexName="RefreshTokenIndex",
            KeyConditionExpression=Key("refresh_token").eq(refresh_token),
        )
        return response["Items"][0] if response["Items"] else None
