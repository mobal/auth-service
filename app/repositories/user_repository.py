import boto3
from boto3.dynamodb.conditions import Attr, Key

from app import settings
from app.models.user import User


class UserRepository:
    def __init__(self):
        self._table = (
            boto3.Session().resource("dynamodb").Table(f"{settings.stage}-users")
        )

    def get_by_email(self, email: str) -> User | None:
        response = self._table.query(
            IndexName="EmailIndex",
            KeyConditionExpression=Key("email").eq(email),
            FilterExpression=Attr("deleted_at").not_exists()
            | Attr("deleted_at").eq(None),
        )
        if response["Items"]:
            return User(**response["Items"][0])
        return None

    def get_by_id(self, user_uuid: str) -> User | None:  # pragma: no cover
        response = self._table.query(
            KeyConditionExpression=Key("id").eq(user_uuid),
            FilterExpression=Attr("deleted_at").not_exists()
            | Attr("deleted_at").eq(None),
        )
        if response["Items"]:
            return User(**response["Items"][0])
        return None
