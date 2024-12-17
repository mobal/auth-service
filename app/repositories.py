from typing import Tuple

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

    async def create(self, jwt_token: JWTToken, refresh_token: JWTToken):
        pass

    async def delete(self, jti: str):
        pass

    async def get_by_id(self, jti: str) -> Tuple[JWTToken, JWTToken] | None:
        response = self.__table.get_item(
            Key={"jti": jti},
        )
        if response["Item"]:
            return JWTToken(**response["Item"]["jwt_token"]), JWTToken(
                **response["Item"]["refresh_token"]
            )
        return None
