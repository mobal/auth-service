import os
from datetime import UTC, datetime

import boto3
from argon2 import PasswordHasher

REGION = os.getenv("AWS_REGION_NAME", "eu-central-1")
STAGE = os.getenv("STAGE", "local")
CLIENT_ID = "user-service"
CLIENT_SECRET = "client-secret"
SSM_CLIENT_SECRET = "client-secret"
REDIRECT_URI = "https://client.example.com/callback"
SCOPES = ["users:read"]


def _client(service: str) -> "boto3.client":
    return boto3.client(
        service,
        region_name=REGION,
        endpoint_url=os.getenv("AWS_ENDPOINT_URL", "http://localstack:4566"),
    )


def create_tables() -> None:
    dynamodb = _client("dynamodb")

    tables = {
        f"{STAGE}-services": {
            "AttributeDefinitions": [
                {"AttributeName": "id", "AttributeType": "S"},
                {"AttributeName": "name", "AttributeType": "S"},
            ],
            "KeySchema": [{"AttributeName": "id", "KeyType": "HASH"}],
            "GlobalSecondaryIndexes": [
                {
                    "IndexName": "NameIndex",
                    "KeySchema": [{"AttributeName": "name", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
        },
        f"{STAGE}-tokens": {
            "AttributeDefinitions": [
                {"AttributeName": "jti", "AttributeType": "S"},
                {"AttributeName": "refresh_token", "AttributeType": "S"},
            ],
            "KeySchema": [{"AttributeName": "jti", "KeyType": "HASH"}],
            "GlobalSecondaryIndexes": [
                {
                    "IndexName": "RefreshTokenIndex",
                    "KeySchema": [
                        {"AttributeName": "refresh_token", "KeyType": "HASH"}
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
        },
        # NOTE: matches app/repositories/authorization_code_repository.py, which
        # uses an underscore (the Terraform definition uses a dash — known drift).
        f"{STAGE}-authorization_codes": {
            "AttributeDefinitions": [
                {"AttributeName": "id", "AttributeType": "S"},
                {"AttributeName": "code", "AttributeType": "S"},
            ],
            "KeySchema": [{"AttributeName": "id", "KeyType": "HASH"}],
            "GlobalSecondaryIndexes": [
                {
                    "IndexName": "CodeIndex",
                    "KeySchema": [{"AttributeName": "code", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
        },
    }

    for name, schema in tables.items():
        if name in dynamodb.list_tables().get("TableNames", []):
            print(f"table {name} already exists")
            continue
        dynamodb.create_table(
            TableName=name,
            BillingMode="PAY_PER_REQUEST",
            **schema,
        )
        print(f"created table {name}")


def put_ssm_parameters() -> None:
    ssm = _client("ssm")

    parameters = {
        os.getenv(
            "CLIENT_SECRET_SSM_PARAM_NAME", f"/{STAGE}/auth-service/client-secret"
        ): ("client-secret", "SecureString"),
        os.getenv("JWT_SECRET_SSM_PARAM_NAME", f"/{STAGE}/secrets/jwt-secret"): (
            "jwt-secret",
            "SecureString",
        ),
        os.getenv(
            "USER_SERVICE_BASE_URL_SSM_PARAM_NAME",
            f"/{STAGE}/user-service/base-url",
        ): ("http://user-service:9000", "String"),
    }

    for name, (value, param_type) in parameters.items():
        ssm.put_parameter(Name=name, Value=value, Type=param_type, Overwrite=True)
        print(f"put parameter {name}")


def seed_service_credentials() -> None:
    """Insert the OAuth clients used by the collection.

    ``user-service`` is the client the collection authenticates as; the
    password grant additionally issues its service token under the app's own
    identity (``AuthService._issue_service_token`` uses
    ``settings.app_name`` + ``settings.client_secret``), so ``auth-service``
    must be registered with the SSM client secret as well.
    """
    dynamodb = boto3.resource(
        "dynamodb",
        region_name=REGION,
        endpoint_url=os.getenv("AWS_ENDPOINT_URL", "http://localstack:4566"),
    )
    table = dynamodb.Table(f"{STAGE}-services")
    table.put_item(
        Item={
            "id": "client",
            "name": CLIENT_ID,
            "secret": PasswordHasher().hash(CLIENT_SECRET),
            "scopes": SCOPES,
            "redirect_uris": [REDIRECT_URI],
            "created_at": datetime.now(UTC).isoformat(),
        }
    )
    table.put_item(
        Item={
            "id": "app",
            "name": os.getenv("APP_NAME", "auth-service"),
            "secret": PasswordHasher().hash(SSM_CLIENT_SECRET),
            "scopes": [],
            "created_at": datetime.now(UTC).isoformat(),
        }
    )
    print(f"seeded service credentials {CLIENT_ID} and auth-service")


if __name__ == "__main__":
    create_tables()
    put_ssm_parameters()
    seed_service_credentials()
    print("localstack seeded")
