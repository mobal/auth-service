import uuid
from typing import Any, Dict

import boto3
import pendulum
import pytest
from argon2 import PasswordHasher
from moto import mock_aws

from app.models import JWTToken, User
from app.settings import Settings


def pytest_configure():
    pytest.stage = "test"

    pytest.aws_access_key_id = "aws_access_key_id"
    pytest.aws_region_name = "eu-central-1"
    pytest.aws_secret_access_key = "aws_secret_access_key"

    pytest.cache_service_api_key_ssm_param_name = "/dev/service/api-key"
    pytest.cache_service_api_key_ssm_param_value = (
        "a2ce72ae-6e34-4c15-8c5a-cb976d119016"
    )
    pytest.cache_service_base_url = "https://localhost"
    pytest.jwt_secret_ssm_param_name = "/dev/secrets/secret"
    pytest.jwt_secret_ssm_param_value = "94k9yz00rw"
    pytest.service_name = "auth-service"
    pytest.tokens_table_name = f"{pytest.stage}-tokens"
    pytest.users_table_name = f"{pytest.stage}-users"


@pytest.fixture(autouse=True)
def setup():
    with mock_aws():
        ssm_client = boto3.client("ssm")
        ssm_client.put_parameter(
            Name=pytest.cache_service_api_key_ssm_param_name,
            Value=pytest.cache_service_api_key_ssm_param_value,
            Type="SecureString",
        )
        ssm_client.put_parameter(
            Name=pytest.jwt_secret_ssm_param_name,
            Value=pytest.jwt_secret_ssm_param_value,
            Type="SecureString",
        )
        yield


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
def initialize_users_table(dynamodb_resource, user_model: User):
    users_table = dynamodb_resource.create_table(
        AttributeDefinitions=[
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "email", "AttributeType": "S"},
        ],
        TableName=pytest.users_table_name,
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
def initialize_tokens_table(
    dynamodb_resource, jwt_token: JWTToken, refresh_token: JWTToken
):
    tokens_table = dynamodb_resource.create_table(
        AttributeDefinitions=[
            {"AttributeName": "jti", "AttributeType": "S"},
        ],
        TableName=pytest.tokens_table_name,
        KeySchema=[{"AttributeName": "jti", "KeyType": "HASH"}],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )
    tokens_table.put_item(
        Item={
            "jti": jwt_token.jti,
            "jwt_token": jwt_token.model_dump(),
            "refresh_token": refresh_token.model_dump(),
            "ttl": jwt_token.exp,
        }
    )


@pytest.fixture
def jwt_token(user_model) -> JWTToken:
    iat = pendulum.now()
    exp = iat.add(hours=1)
    return JWTToken(
        exp=exp.int_timestamp,
        iat=iat.int_timestamp,
        iss=None,
        jti=str(uuid.uuid4()),
        sub=user_model.id,
    )


@pytest.fixture
def refresh_token(jwt_token: JWTToken) -> JWTToken:
    iat = pendulum.now()
    exp = iat.add(days=1)
    return JWTToken(
        exp=exp.int_timestamp,
        iat=iat.int_timestamp,
        iss=None,
        jti=str(uuid.uuid4()),
        sub=jwt_token.sub,
    )


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
def users_table(dynamodb_resource, initialize_users_table):
    return dynamodb_resource.Table(pytest.users_table_name)


@pytest.fixture
def tokens_table(dynamodb_resource, initialize_tokens_table):
    return dynamodb_resource.Table(pytest.tokens_table_name)
