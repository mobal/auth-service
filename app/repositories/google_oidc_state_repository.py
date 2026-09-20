import secrets
from datetime import UTC, datetime, timedelta

import boto3
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError

from app import settings
from app.models.google_oidc_state import GoogleOIDCState


class GoogleOIDCStateRepository:
    def __init__(self) -> None:
        self._logger = Logger()
        self._table = boto3.resource("dynamodb").Table(
            f"{settings.stage}-{settings.app_name}-google-oidc-states"
        )

    def create(
        self,
        pending_request_id: str,
        lifetime_seconds: int,
    ) -> GoogleOIDCState:
        now = datetime.now(UTC)
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        expires_at = now + timedelta(seconds=lifetime_seconds)
        item = GoogleOIDCState(
            state=state,
            nonce=nonce,
            pending_request_id=pending_request_id,
            created_at=now.isoformat(),
            ttl=int(expires_at.timestamp()),
        )
        self._table.put_item(Item=item.model_dump())
        return item

    def get(self, state: str) -> GoogleOIDCState | None:
        response = self._table.get_item(Key={"state": state}, ConsistentRead=True)
        item = response.get("Item")
        if not item or item["ttl"] <= int(datetime.now(UTC).timestamp()):
            return None
        return GoogleOIDCState(**item)

    def consume(self, state: str) -> GoogleOIDCState | None:
        item = self.get(state)
        if item is None:
            return None
        try:
            self._table.delete_item(
                Key={"state": state},
                ConditionExpression="attribute_exists(#state)",
                ExpressionAttributeNames={"#state": "state"},
            )
        except ClientError as error:
            if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return None
            raise
        return item
