import os
import secrets
import uuid
from typing import Any

import boto3
import pendulum
import pytest
from argon2 import PasswordHasher
from moto import mock_aws

from app.models.jwt import JWTToken
from app.models.user import User
from app.settings import Settings


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    with mock_aws():
        monkeypatch.setenv(
            "JWT_SECRET_SSM_PARAM_NAME", os.getenv("JWT_SECRET_SSM_PARAM_NAME")
        )
        ssm_client = boto3.client(
            "ssm",
            region_name=os.getenv("AWS_REGION_NAME"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )
        ssm_client.put_parameter(
            Name=os.getenv("JWT_SECRET_SSM_PARAM_NAME"),
            Value=os.getenv("JWT_SECRET_SSM_PARAM_VALUE"),
            Type="SecureString",
        )
        yield


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME"),
        default_timezone=os.getenv("DEFAULT_TIMEZONE"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        stage=os.getenv("STAGE"),
    )


@pytest.fixture
def dynamodb_resource(settings):
    with mock_aws():
        yield boto3.Session().resource(
            "dynamodb",
            region_name=os.getenv("AWS_REGION_NAME"),
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )


@pytest.fixture
def initialize_users_table(dynamodb_resource, user: User, users_table_name: str):
    users_table = dynamodb_resource.create_table(
        AttributeDefinitions=[
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "email", "AttributeType": "S"},
            {"AttributeName": "username", "AttributeType": "S"},
        ],
        TableName=users_table_name,
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
            {
                "IndexName": "UsernameIndex",
                "KeySchema": [
                    {"AttributeName": "username", "KeyType": "HASH"},
                ],
                "Projection": {
                    "ProjectionType": "ALL",
                },
            },
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )
    users_table.put_item(Item=user.model_dump())


@pytest.fixture
def initialize_tokens_table(
    dynamodb_resource, jwt_token: JWTToken, refresh_token: str, tokens_table_name: str
):
    tokens_table = dynamodb_resource.create_table(
        AttributeDefinitions=[
            {"AttributeName": "jti", "AttributeType": "S"},
            {"AttributeName": "refresh_token", "AttributeType": "S"},
        ],
        TableName=tokens_table_name,
        KeySchema=[{"AttributeName": "jti", "KeyType": "HASH"}],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "RefreshTokenIndex",
                "KeySchema": [{"AttributeName": "refresh_token", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )
    tokens_table.put_item(
        Item={
            "jti": jwt_token.jti,
            "jwt_token": jwt_token.model_dump(),
            "refresh_token": refresh_token,
            "created_at": pendulum.now().to_iso8601_string(),
            "ttl": jwt_token.exp,
        }
    )


@pytest.fixture
def jwt_token(user: User) -> JWTToken:
    iat = pendulum.now()
    exp = iat.add(hours=1)
    return JWTToken(
        exp=exp.int_timestamp,
        iat=iat.int_timestamp,
        iss=None,
        jti=str(uuid.uuid4()),
        sub=user.id,
        user=user.model_dump(
            exclude={"password", "created_at", "deleted_at", "updated_at"}
        ),
    )


@pytest.fixture
def refresh_token() -> str:
    return secrets.token_hex(16)


@pytest.fixture
def tokens_table_name() -> str:
    return f"{os.getenv('STAGE')}-tokens"


@pytest.fixture
def user_dict() -> dict[str, Any]:
    now = pendulum.now()
    return {
        "display_name": "root",
        "email": "root@netcode.hu",
        "password": PasswordHasher().hash("12345678"),
        "username": "root",
        "roles": ["root"],
        "created_at": now.to_iso8601_string(),
        "updated_at": now.to_iso8601_string(),
    }


@pytest.fixture
def user(user_dict: dict[str, Any]) -> User:
    return User(
        id=str(uuid.uuid4()),
        display_name=user_dict["display_name"],
        email=user_dict["email"],
        password=user_dict["password"],
        username=user_dict["username"],
        roles=user_dict.get("roles", []),
        created_at=user_dict["created_at"],
    )


@pytest.fixture
def users_table(dynamodb_resource, initialize_users_table, users_table_name: str):
    return dynamodb_resource.Table(users_table_name)


@pytest.fixture
def users_table_name() -> str:
    return f"{os.getenv('STAGE')}-users"


@pytest.fixture
def tokens_table(dynamodb_resource, initialize_tokens_table, tokens_table_name: str):
    return dynamodb_resource.Table(tokens_table_name)


@pytest.fixture
def jwt_secret_ssm_param_value() -> str:
    return os.getenv("JWT_SECRET_SSM_PARAM_VALUE")
