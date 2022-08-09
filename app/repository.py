from http.client import HTTPException
import uuid
import pendulum
from starlette import status
import boto3
import logging

from boto3.dynamodb.conditions import Attr, Key
from app.models import User

from app.settings import Settings


class UserRepository:
    def __init__(self):
        self._logger = logging.getLogger()
        settings = Settings()
        session = boto3.Session()
        dynamodb = session.resource('dynamodb')
        self.table = dynamodb.Table(f'{settings.app_stage}-users')

    async def create_user(self, data: dict) -> User:
        user = User(
            id=str(
                uuid.uuid4()),
            display_name=data['display_name'],
            email=data['email'],
            password=data['password'],
            roles=[],
            username=data['username'],
            created_at=pendulum.now().to_iso8601_string(),
            deleted_at=None,
            updated_at=None)
        self.table.put_item(user)
        self._logger.info(f'User successfully created user={user}')
        return user

    async def delete_user(self, uuid: str) -> None:
        user = await self.get_by_id(uuid)
        user.deleted_at = pendulum.now().to_iso8601_string()
        self.table.put_item(user)
        self._logger.info(f'User successfully deleted with uuid={uuid}')

    async def get_by_email(self, email: str) -> User:
        response = self.table.scan(FilterExpression=Attr(
            'email').eq(email) & Attr('deleted_at').eq(None))
        if response['Count'] != 0:
            return User.parse_obj(response['Items'][0])
        error_message = f'The requested user was not found with email={email}'
        self._logger.error(error_message)
        raise HTTPException(status.HTTP_404_NOT_FOUND, error_message)

    async def get_by_id(self, uuid: str) -> User:
        response = self.table.query(
            KeyConditionExpression=Key('id').eq(uuid),
            FilterExpression=Attr('deleted_at').eq(None)
        )
        if response['Count'] != 0:
            return User.parse_obj(response['Items'][0])
        error_message = f'The requested user was not found with uuid={uuid}'
        self._logger.error(error_message)
        raise HTTPException(status.HTTP_404_NOT_FOUND, error_message)

    async def update_user(self, uuid: str, data: dict) -> None:
        user = self.get_by_id(uuid)
        user = user.copy(update=data)
        user.updated_at = pendulum.now().to_iso8601_string()
        self.table.put_item(user)
        self._logger.info(
            f'User with uuid={uuid} successfully updated data={data}')
