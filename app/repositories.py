import boto3
from aws_lambda_powertools import Logger
from boto3.dynamodb.conditions import Attr, Key

from app import settings
from app.models import User


class UserRepository:
    def __init__(self):
        self._logger = Logger(utc=True)
        session = boto3.Session()
        dynamodb = session.resource("dynamodb")
        self._table = dynamodb.Table(f"{settings.stage}-users")

    async def get_by_email(self, email: str) -> User | None:
        response = self._table.scan(
            FilterExpression=Attr("deleted_at").eq(None) & Attr("email").eq(email)
        )
        if response["Items"]:
            return User(**response["Items"][0])
        return None

    async def get_by_id(self, user_uuid: str) -> User | None:
        response = self._table.query(
            KeyConditionExpression=Key("id").eq(user_uuid),
            FilterExpression=Attr("deleted_at").eq(None),
        )
        if response["Items"]:
            return User(**response["Items"][0])
        return None
