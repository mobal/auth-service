from typing import Any

import boto3
from boto3.dynamodb.conditions import Attr, Key

from app import settings
from app.models import JWTToken, User


class UserRepository:
    def __init__(self):
        self.__table = (
            boto3.Session().resource("dynamodb").Table(f"{settings.stage}-users")
        )

    async def get_by_email(self, email: str) -> User | None:
        response = self.__table.scan(
            FilterExpression=Attr("deleted_at").eq(None) & Attr("email").eq(email)
        )
        if response["Items"]:
            return User(**response["Items"][0])
        return None

    async def get_by_id(self, user_uuid: str) -> User | None:
        response = self.__table.query(
            KeyConditionExpression=Key("id").eq(user_uuid),
            FilterExpression=Attr("deleted_at").eq(None),
        )
        if response["Items"]:
            return User(**response["Items"][0])
        return None


class TokenRepository:
    def __init__(self):
        self.__table = (
            boto3.Session().resource("dynamodb").Table(f"{settings.stage}-tokens")
        )

    async def create_token(self, data: dict[str, Any]) -> dict[str, any]:
        return self.__table.put_item(Item=data)

    async def delete_by_id(self, jti: str) -> dict[str, Any]:
        return self.__table.delete_item(Key={"jti": jti})

    async def get_by_id(self, jti: str) -> tuple[JWTToken, str] | None:
        response = self.__table.get_item(
            Key={"jti": jti},
        )
        if "Item" in response:
            return (
                JWTToken(**response["Item"]["jwt_token"]),
                response["Item"]["refresh_token"],
            )
        return None

    async def get_by_refresh_token(self, refresh_token: str) -> dict[str, Any] | None:
        response = self.__table.query(
            IndexName="RefreshTokenIndex",
            KeyConditionExpression=Key("refresh_token").eq(refresh_token),
        )
        return response["Items"][0] if response["Items"] else None
