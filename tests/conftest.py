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


def pytest_addoption(parser):
    parser.addini(
        "stage",
        help="Deployment stage name (test, staging, prod)",
        default="test",
        type="string",
    )
    parser.addini(
        "app_name",
        help="Application name",
        default="auth-service",
        type="string",
    )
    parser.addini(
        "default_timezone",
        help="Default timezone",
        default="Europe/Budapest",
        type="string",
    )
    parser.addini(
        "aws_region_name", help="AWS region name", default="eu-central-1", type="string"
    )
    parser.addini(
        "aws_access_key_id",
        help="AWS access key id",
        default="access_key_id",
        type="string",
    )
    parser.addini(
        "aws_secret_access_key",
        help="AWS secret access key",
        default="secret-access-key",
        type="string",
    )
    parser.addini(
        "service_name",
        help="Service name for resource naming",
        default="auth-service",
        type="string",
    )
    parser.addini(
        "users_table_name",
        help="Override for users table name",
        default="",
        type="string",
    )
    parser.addini(
        "tokens_table_name",
        help="Override for tokens table name",
        default="",
        type="string",
    )
    parser.addini(
        "jwt_secret_length", help="JWT secret length in bytes", default=32, type="int"
    )
    parser.addini(
        "jwt_secret_ssm_param_name",
        help="JWT secret SSM parameter name",
        default="",
        type="string",
    )
    parser.addini(
        "jwt_secret_ssm_param_value",
        help="JWT secret SSM parameter value",
        default="",
        type="string",
    )


@pytest.fixture(scope="session")
def test_config(request) -> dict[str, str]:
    cfg = request.config
    stage = cfg.getini("stage")
    service_name = cfg.getini("service_name")

    users_table = cfg.getini("users_table_name")
    tokens_table = cfg.getini("tokens_table_name")
    jwt_param_name = cfg.getini("jwt_secret_ssm_param_name")

    jwt_secret = cfg.getini("jwt_secret_ssm_param_value")
    if not jwt_secret:
        secret_length = cfg.getini("jwt_secret_length")
        jwt_secret = secrets.token_hex(secret_length)

    return {
        "stage": stage,
        "app_name": cfg.getini("app_name"),
        "default_timezone": cfg.getini("default_timezone"),
        "aws_region_name": cfg.getini("aws_region_name"),
        "aws_access_key_id": cfg.getini("aws_access_key_id"),
        "aws_secret_access_key": cfg.getini("aws_secret_access_key"),
        "service_name": service_name,
        "users_table_name": users_table,
        "tokens_table_name": tokens_table,
        "jwt_secret_ssm_param_name": jwt_param_name,
        "jwt_secret_ssm_param_value": jwt_secret,
    }


@pytest.fixture(autouse=True)
def setup(test_config, monkeypatch):
    with mock_aws():
        monkeypatch.setenv(
            "JWT_SECRET_SSM_PARAM_NAME", test_config["jwt_secret_ssm_param_name"]
        )
        ssm_client = boto3.client(
            "ssm",
            region_name=test_config["aws_region_name"],
            aws_access_key_id=test_config["aws_access_key_id"],
            aws_secret_access_key=test_config["aws_secret_access_key"],
        )
        ssm_client.put_parameter(
            Name=test_config["jwt_secret_ssm_param_name"],
            Value=test_config["jwt_secret_ssm_param_value"],
            Type="SecureString",
        )
        yield


@pytest.fixture
def settings(test_config) -> Settings:
    return Settings(
        app_name=test_config["app_name"],
        default_timezone=test_config["default_timezone"],
        aws_access_key_id=test_config["aws_access_key_id"],
        aws_secret_access_key=test_config["aws_secret_access_key"],
        stage=test_config["stage"],
    )


@pytest.fixture
def dynamodb_resource(settings, test_config):
    with mock_aws():
        yield boto3.Session().resource(
            "dynamodb",
            region_name=test_config["aws_region_name"],
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )


@pytest.fixture
def initialize_users_table(dynamodb_resource, user: User, test_config):
    users_table = dynamodb_resource.create_table(
        AttributeDefinitions=[
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "email", "AttributeType": "S"},
        ],
        TableName=test_config["users_table_name"],
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
    users_table.put_item(Item=user.model_dump())


@pytest.fixture
def initialize_tokens_table(
    dynamodb_resource, jwt_token: JWTToken, refresh_token: str, test_config
):
    tokens_table = dynamodb_resource.create_table(
        AttributeDefinitions=[
            {"AttributeName": "jti", "AttributeType": "S"},
            {"AttributeName": "refresh_token", "AttributeType": "S"},
        ],
        TableName=test_config["tokens_table_name"],
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
def user_dict() -> dict[str, Any]:
    now = pendulum.now()
    return {
        "display_name": "root",
        "email": "root@netcode.hu",
        "password": PasswordHasher().hash("12345678"),
        "username": "root",
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
        created_at=user_dict["created_at"],
    )


@pytest.fixture
def users_table(dynamodb_resource, initialize_users_table, test_config):
    return dynamodb_resource.Table(test_config["users_table_name"])


@pytest.fixture
def tokens_table(dynamodb_resource, initialize_tokens_table, test_config):
    return dynamodb_resource.Table(test_config["tokens_table_name"])


@pytest.fixture(scope="session")
def jwt_secret_ssm_param_value(test_config) -> str:
    return test_config["jwt_secret_ssm_param_value"]
