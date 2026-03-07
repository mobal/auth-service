import os
import secrets
import uuid
from typing import Any

import boto3
import pendulum
import pytest
from argon2 import PasswordHasher
from moto import mock_aws

from app.models.jwt import JWTToken, RefreshToken
from app.models.service import ServiceCredential
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
def initialize_authorization_codes_table(
    dynamodb_resource, authorization_codes_table_name: str
):
    dynamodb_resource.create_table(
        AttributeDefinitions=[
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "code", "AttributeType": "S"},
        ],
        TableName=authorization_codes_table_name,
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "CodeIndex",
                "KeySchema": [{"AttributeName": "code", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
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
def initialize_services_table(
    dynamodb_resource, service_credential: ServiceCredential, services_table_name: str
):
    services_table = dynamodb_resource.create_table(
        AttributeDefinitions=[
            {"AttributeName": "id", "AttributeType": "S"},
        ],
        TableName=services_table_name,
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )
    services_table.put_item(
        Item={
            "id": service_credential.id,
            "secret": service_credential.secret,
            "scopes": service_credential.scopes,
            "created_at": service_credential.created_at,
        }
    )


@pytest.fixture
def initialize_tokens_table(
    dynamodb_resource,
    jwt_token: JWTToken,
    refresh_token: RefreshToken,
    tokens_table_name: str,
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
            "refresh_token": refresh_token.token,
            "created_at": pendulum.from_timestamp(jwt_token.iat).to_iso8601_string(),
            "expire_at": pendulum.from_timestamp(refresh_token.ttl).to_iso8601_string(),
            "ttl": refresh_token.ttl,
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
        scope="tokens:revoke users:read users:write",
        user=user.model_dump(
            exclude={"password", "created_at", "deleted_at", "updated_at"}
        ),
    )


@pytest.fixture
def password() -> str:
    return "not_so_secure_password"


@pytest.fixture
def refresh_token() -> RefreshToken:
    return RefreshToken(
        token=secrets.token_hex(16),
        ttl=pendulum.now().add(days=30).int_timestamp,
    )


@pytest.fixture
def service_credential_dict(password: str) -> dict[str, Any]:
    return {
        "secret": PasswordHasher().hash(password),
        "scopes": ["users:read", "users:write"],
        "created_at": pendulum.now().to_iso8601_string(),
    }


@pytest.fixture
def service_credential(service_credential_dict: dict[str, Any]) -> ServiceCredential:
    return ServiceCredential(
        id=str(uuid.uuid4()),
        secret=service_credential_dict["secret"],
        scopes=service_credential_dict["scopes"],
        created_at=service_credential_dict["created_at"],
    )


@pytest.fixture
def services_table_name() -> str:
    return f"{os.getenv('STAGE')}-services"


@pytest.fixture
def tokens_table_name() -> str:
    return f"{os.getenv('STAGE')}-tokens"


@pytest.fixture
def user_dict(password: str) -> dict[str, Any]:
    now = pendulum.now()
    return {
        "display_name": "root",
        "email": "root@squarelabs.hu",
        "password": PasswordHasher().hash(password),
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
def authorization_codes_table_name() -> str:
    return f"{os.getenv('STAGE')}-authorization_codes"


@pytest.fixture
def authorization_codes_table(
    dynamodb_resource,
    initialize_authorization_codes_table,
    authorization_codes_table_name: str,
):
    return dynamodb_resource.Table(authorization_codes_table_name)


@pytest.fixture
def services_table(
    dynamodb_resource, initialize_services_table, services_table_name: str
):
    return dynamodb_resource.Table(services_table_name)


@pytest.fixture
def jwt_secret_ssm_param_value() -> str:
    return os.getenv("JWT_SECRET_SSM_PARAM_VALUE")
