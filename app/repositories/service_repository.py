import boto3
from aws_lambda_powertools import Logger

from app import settings
from app.models.service import ServiceCredential


class ServiceRepository:
    def __init__(self):
        self._logger = Logger()
        self._table = (
            boto3.Session().resource("dynamodb").Table(f"{settings.stage}-services")
        )

    def create_service(self, data: dict) -> dict:
        self._logger.info("Creating service credential record")
        return self._table.put_item(Item=data)

    def get_by_id(self, client_id: str) -> ServiceCredential | None:
        self._logger.debug(f"Fetching service credential by client_id={client_id}")
        response = self._table.get_item(Key={"id": client_id})
        if "Item" in response:
            return ServiceCredential(**response["Item"])
        self._logger.warning(f"Service credential not found for client_id={client_id}")
        return None
