import boto3
import pytest
from moto import mock_aws

from app.repositories import UserRepository
from app.services import User
from app.settings import Settings


@pytest.mark.asyncio
class TestUserRepository:
    @pytest.fixture
    def dynamodb_resource(self, settings: Settings):
        with mock_aws():
            yield boto3.resource(
                "dynamodb",
                region_name="eu-central-1",
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
            )

    @pytest.fixture
    def dynamodb_table(self, dynamodb_resource):
        return dynamodb_resource.Table("test-users")

    @pytest.fixture(autouse=True)
    def setup_table(self, dynamodb_resource, dynamodb_table, user_model: User):
        dynamodb_resource.create_table(
            TableName="test-users",
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        )
        dynamodb_table.put_item(Item=user_model.model_dump())

    async def test_successfully_get_item_by_email(
        self, dynamodb_table, user_model: User, user_repository: UserRepository
    ):
        item = await user_repository.get_by_email(user_model.email)
        assert user_model.model_dump() == item

    async def test_successfully_get_item_by_id(
        self, dynamodb_table, user_model: User, user_repository: UserRepository
    ):
        item = await user_repository.get_by_id(user_model.id)
        assert user_model.model_dump() == item
