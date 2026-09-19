import secrets
from datetime import UTC, datetime, timedelta

import boto3
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError

from app import settings
from app.models.pending_authorization_request import PendingAuthorizationRequest


class PendingAuthorizationRequestRepository:
    def __init__(self) -> None:
        self._logger = Logger()
        self._table = boto3.resource("dynamodb").Table(
            f"{settings.stage}-{settings.app_name}-pending-authorization-requests"
        )

    def create(
        self,
        client_id: str,
        redirect_uri: str,
        response_type: str,
        scope: str | None,
        state: str | None,
        code_challenge: str,
        code_challenge_method: str,
        lifetime_seconds: int = 600,
    ) -> str:
        now = datetime.now(UTC)
        request_id = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        expires_at = now + timedelta(seconds=lifetime_seconds)
        self._table.put_item(
            Item={
                "id": request_id,
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "response_type": response_type,
                "scope": scope,
                "state": state,
                "code_challenge": code_challenge,
                "code_challenge_method": code_challenge_method,
                "csrf_token": csrf_token,
                "created_at": now.isoformat(),
                "ttl": int(expires_at.timestamp()),
            },
        )
        return request_id

    def get(self, request_id: str) -> PendingAuthorizationRequest | None:
        response = self._table.get_item(Key={"id": request_id}, ConsistentRead=True)
        item = response.get("Item")
        if not item or item["ttl"] <= int(datetime.now(UTC).timestamp()):
            return None
        return PendingAuthorizationRequest(**item)

    def consume(self, request_id: str) -> PendingAuthorizationRequest | None:
        pending = self.get(request_id)
        if pending is None:
            return None
        try:
            self._table.delete_item(
                Key={"id": request_id},
                ConditionExpression="attribute_exists(id)",
            )
        except ClientError as error:
            if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return None
            raise
        return pending
