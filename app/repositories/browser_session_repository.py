import secrets
from datetime import UTC, datetime, timedelta

import boto3
from aws_lambda_powertools import Logger

from app import settings
from app.models.browser_session import BrowserSession


class BrowserSessionRepository:
    def __init__(self) -> None:
        self._logger = Logger()
        self._table = boto3.resource("dynamodb").Table(
            f"{settings.stage}-{settings.app_name}-browser-sessions"
        )

    def create(self, user_id: str, lifetime_seconds: int = 3600) -> str:
        now = datetime.now(UTC)
        session_id = secrets.token_urlsafe(32)
        expires_at = now + timedelta(seconds=lifetime_seconds)
        self._table.put_item(
            Item={
                "id": session_id,
                "user_id": user_id,
                "created_at": now.isoformat(),
                "ttl": int(expires_at.timestamp()),
            },
        )
        return session_id

    def get(self, session_id: str) -> BrowserSession | None:
        response = self._table.get_item(Key={"id": session_id}, ConsistentRead=True)
        item = response.get("Item")
        if not item or item["ttl"] <= int(datetime.now(UTC).timestamp()):
            return None
        return BrowserSession(**item)

    def delete(self, session_id: str) -> None:
        self._table.delete_item(Key={"id": session_id})
