import boto3
from aws_lambda_powertools import Logger
from boto3.dynamodb.conditions import Key

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
        self._logger.debug("Fetching service credential by client_id=%s", client_id)

        response = self._table.get_item(Key={"id": client_id})
        if "Item" in response:
            return ServiceCredential(**response["Item"])
        self._logger.warning("Service credential not found for client_id=%s", client_id)

        return None

    def get_by_name(self, name: str) -> ServiceCredential | None:
        self._logger.debug("Fetching service credential by name=%s", name)

        response = self._table.query(
            IndexName="NameIndex",
            KeyConditionExpression=Key("name").eq(name),
        )
        if "Items" in response and response["Items"]:
            return ServiceCredential(**response["Items"][0])

        self._logger.warning("Service credential not found for name=%s", name)
        return None
