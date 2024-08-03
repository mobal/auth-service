import uuid
from typing import Any, Dict

import boto3
import pendulum
import pytest
from argon2 import PasswordHasher
from moto import mock_aws

from app.models import User
from app.settings import Settings


def pytest_configure():
    pytest.stage = "test"

    pytest.aws_access_key_id = "aws_access_key_id"
    pytest.aws_region_name = "eu-central-1"
    pytest.aws_secret_access_key = "aws_secret_access_key"

    pytest.cache_service_base_url = "https://localhost"

    pytest.jwt_secret = "6fl3AkTFmG2rVveLglUW8DOmp8J4Bvi3"

    pytest.service_name = "auth-service"
    pytest.table_name = f"{pytest.stage}-users"


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def dynamodb_resource(settings):
    with mock_aws():
        yield boto3.Session().resource(
            "dynamodb",
            region_name="eu-central-1",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )


@pytest.fixture
def initialize_users_table(dynamodb_resource, user_model: User, users_table):
    dynamodb_resource.create_table(
        AttributeDefinitions=[
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "email", "AttributeType": "S"},
        ],
        TableName="test-users",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "EmailIndex",
                "KeySchema": [
                    {"AttributeName": "email", "KeyType": "HASH"},
                ],
                "Projection": {
                    "ProjectionType": "ALL",
                },
            },
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )
    users_table.put_item(Item=user_model.model_dump())


@pytest.fixture
def user_dict() -> Dict[str, Any]:
    now = pendulum.now()
    return {
        "display_name": "root",
        "email": "root@netcode.hu",
        "password": PasswordHasher().hash("12345678"),
        "roles": ["test"],
        "username": "root",
        "created_at": now.to_iso8601_string(),
        "updated_at": now.to_iso8601_string(),
    }


@pytest.fixture
def user_model(user_dict: Dict[str, Any]) -> User:
    return User(
        id=str(uuid.uuid4()),
        display_name=user_dict["display_name"],
        email=user_dict["email"],
        password=user_dict["password"],
        roles=user_dict["roles"],
        username=user_dict["username"],
        created_at=user_dict["created_at"],
    )


@pytest.fixture
def users_table(dynamodb_resource):
    return dynamodb_resource.Table(pytest.table_name)
