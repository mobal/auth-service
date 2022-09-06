from typing import Optional

import boto3
import logging

from boto3.dynamodb.conditions import Attr, Key

from app.settings import Settings


class UserRepository:
    def __init__(self):
        self._logger = logging.getLogger()
        settings = Settings()
        session = boto3.Session()
        dynamodb = session.resource('dynamodb')
        self._table = dynamodb.Table(f'{settings.app_stage}-users')

    async def get_by_email(self, email: str) -> Optional[dict]:
        response = self._table.scan(
            FilterExpression=Attr('deleted_at').eq(None) & Attr('email').eq(email)
        )
        if response['Items']:
            return response['Items'][0]

    async def get_by_id(self, user_uuid: str) -> Optional[dict]:
        response = self._table.query(
            KeyConditionExpression=Key('id').eq(user_uuid),
            FilterExpression=Attr('deleted_at').eq(None),
        )
        if response['Items']:
            return response['Items'][0]
