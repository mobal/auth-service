import os
import secrets
import time
import uuid
from datetime import UTC, datetime
from typing import Any

import boto3
import pytest
from argon2 import PasswordHasher
from moto import mock_aws

from app.models.jwt import JWTToken, RefreshToken
from app.models.service import ServiceCredential
from app.settings import Settings


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    with mock_aws():
        monkeypatch.setenv(
            "CLIENT_SECRET_SSM_PARAM_NAME",
            os.getenv(
                "CLIENT_SECRET_SSM_PARAM_NAME", "/test/auth-service/client-secret"
            ),
        )
        monkeypatch.setenv(
            "JWT_SECRET_SSM_PARAM_NAME",
            os.getenv("JWT_SECRET_SSM_PARAM_NAME", "/test/secrets/jwt-secret"),
        )
        monkeypatch.setenv(
            "USER_SERVICE_BASE_URL_SSM_PARAM_NAME",
            os.getenv(
                "USER_SERVICE_BASE_URL_SSM_PARAM_NAME",
                "/test/user-service/base-url",
            ),
        )
        ssm_client = boto3.client(
            "ssm",
            region_name=os.getenv("AWS_REGION_NAME", "eu-central-1"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "testing"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "testing"),
        )
        ssm_client.put_parameter(
            Name=os.getenv(
                "CLIENT_SECRET_SSM_PARAM_NAME",
                "/test/auth-service/client-secret",
            ),
            Value=os.getenv("CLIENT_SECRET_SSM_PARAM_VALUE", "test-client-secret"),
            Type="SecureString",
        )
        ssm_client.put_parameter(
            Name=os.getenv(
                "JWT_SECRET_SSM_PARAM_NAME",
                "/test/secrets/jwt-secret",
            ),
            Value=os.getenv("JWT_SECRET_SSM_PARAM_VALUE", "test-jwt-secret"),
            Type="SecureString",
        )
        ssm_client.put_parameter(
            Name=os.getenv(
                "USER_SERVICE_BASE_URL_SSM_PARAM_NAME",
                "/test/user-service/base-url",
            ),
            Value=os.getenv(
                "USER_SERVICE_BASE_URL_SSM_PARAM_VALUE",
                "https://test.user-service.local",
            ),
            Type="String",
        )

        yield


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME"),
        default_timezone=os.getenv("DEFAULT_TIMEZONE"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        stage=os.getenv("STAGE", "test"),
        jwt_token_lifetime=3600,
    )


@pytest.fixture
def dynamodb_resource(settings):
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
def initialize_services_table(
    dynamodb_resource,
    service_credential: ServiceCredential,
    services_table_name: str,
    fast_password_hasher: PasswordHasher,
):
    services_table = dynamodb_resource.create_table(
        AttributeDefinitions=[
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "name", "AttributeType": "S"},
        ],
        TableName=services_table_name,
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "NameIndex",
                "KeySchema": [{"AttributeName": "name", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )
    services_table.put_item(
        Item={
            "id": service_credential.id,
            "name": service_credential.name,
            "secret": service_credential.secret,
            "scopes": service_credential.scopes,
            "created_at": service_credential.created_at,
        }
    )
    services_table.put_item(
        Item={
            "id": str(uuid.uuid4()),
            "name": "user-service",
            "secret": fast_password_hasher.hash(
                os.getenv("SERVICE_TOKEN_SECRET", "test-service-token-secret")
            ),
            "scopes": ["users:read"],
            "created_at": datetime.now(UTC).isoformat(),
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
            "created_at": datetime.fromtimestamp(jwt_token.iat, tz=UTC).isoformat(),
            "expire_at": datetime.fromtimestamp(refresh_token.ttl, tz=UTC).isoformat(),
            "ttl": refresh_token.ttl,
        }
    )


@pytest.fixture
def user_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def user_data(user_id: str) -> dict:
    return {
        "id": user_id,
        "email": "root@squarelabs.hu",
        "username": "root",
        "display_name": "root",
        "roles": ["root"],
    }


@pytest.fixture
def jwt_token(settings: Settings) -> JWTToken:
    iat = int(time.time())
    exp = iat + 3600
    issuer = f"{settings.stage}-{settings.app_name}"
    return JWTToken(
        exp=exp,
        iat=iat,
        iss=issuer,
        aud=issuer,
        jti=str(uuid.uuid4()),
        sub=str(uuid.uuid4()),
        scope="tokens:revoke users:read users:write",
    )


@pytest.fixture
def expired_jwt_token(settings: Settings) -> JWTToken:
    iat = int(time.time()) - 2 * 86400
    exp = iat + 3600
    issuer = f"{settings.stage}-{settings.app_name}"
    return JWTToken(
        exp=exp,
        iat=iat,
        iss=issuer,
        aud=issuer,
        jti=str(uuid.uuid4()),
        sub=str(uuid.uuid4()),
        scope="tokens:revoke users:read",
    )


@pytest.fixture
def jwt_token_no_scope(settings: Settings) -> JWTToken:
    iat = int(time.time())
    exp = iat + 3600
    issuer = f"{settings.stage}-{settings.app_name}"
    return JWTToken(
        exp=exp,
        iat=iat,
        iss=issuer,
        aud=issuer,
        jti=str(uuid.uuid4()),
        sub=str(uuid.uuid4()),
        scope=None,
    )


@pytest.fixture
def jwt_token_empty_sub(settings: Settings) -> JWTToken:
    iat = int(time.time())
    exp = iat + 3600
    issuer = f"{settings.stage}-{settings.app_name}"
    return JWTToken(
        exp=exp,
        iat=iat,
        iss=issuer,
        aud=issuer,
        jti=str(uuid.uuid4()),
        sub="",
        scope="tokens:revoke",
    )


@pytest.fixture
def fast_password_hasher() -> PasswordHasher:
    """Argon2 hasher with minimal parameters for fast test execution."""
    return PasswordHasher(time_cost=1, memory_cost=64, parallelism=1)  # noqa


@pytest.fixture
def password() -> str:
    return "not_so_secure_password"


@pytest.fixture
def refresh_token() -> RefreshToken:
    return RefreshToken(
        token=secrets.token_hex(16),
        ttl=int(time.time()) + 30 * 86400,
    )


@pytest.fixture
def service_credential_dict(
    password: str, fast_password_hasher: PasswordHasher
) -> dict[str, Any]:
    return {
        "name": "test-service",
        "secret": fast_password_hasher.hash(password),
        "scopes": ["users:read", "users:write"],
        "created_at": datetime.now(UTC).isoformat(),
    }


@pytest.fixture
def service_credential(service_credential_dict: dict[str, Any]) -> ServiceCredential:
    return ServiceCredential(
        id=str(uuid.uuid4()),
        name=service_credential_dict["name"],
        secret=service_credential_dict["secret"],
        scopes=service_credential_dict["scopes"],
        created_at=service_credential_dict["created_at"],
    )


@pytest.fixture
def services_table_name() -> str:
    return f"{os.getenv('STAGE', 'test')}-services"


@pytest.fixture
def tokens_table_name() -> str:
    return f"{os.getenv('STAGE', 'test')}-tokens"


@pytest.fixture
def tokens_table(dynamodb_resource, initialize_tokens_table, tokens_table_name: str):
    return dynamodb_resource.Table(tokens_table_name)


@pytest.fixture
def authorization_codes_table_name() -> str:
    return f"{os.getenv('STAGE', 'test')}-authorization_codes"


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
