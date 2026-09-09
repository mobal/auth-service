import boto3
from aws_lambda_powertools import Logger

from app import settings
from app.models.audience import Audience


class AudienceRepository:
    """Reads audience registrations from the ``audiences`` table.

    The table is the single source of truth for which audiences exist and
    which clients are allowed to request tokens for them.
    """

    def __init__(self) -> None:
        self._logger = Logger()
        self._table = (
            boto3.Session().resource("dynamodb").Table(f"{settings.stage}-audiences")
        )

    def create(self, data: dict) -> dict:
        self._logger.info(
            "Creating audience record", extra={"audience": data.get("audience")}
        )
        return self._table.put_item(Item=data)

    def get_by_audience(self, audience: str) -> Audience | None:
        self._logger.debug("Fetching audience by audience=%s", audience)
        response = self._table.get_item(Key={"audience": audience})
        if "Item" in response:
            return Audience(**response["Item"])
        self._logger.warning("Audience not found for audience=%s", audience)
        return None
