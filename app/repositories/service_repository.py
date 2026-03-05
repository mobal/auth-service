import boto3

from app import settings
from app.models.service import ServiceCredential


class ServiceRepository:
    def __init__(self):
        self._table = (
            boto3.Session().resource("dynamodb").Table(f"{settings.stage}-services")
        )

    def create_service(self, data: dict) -> dict:
        return self._table.put_item(Item=data)

    def get_by_id(self, client_id: str) -> ServiceCredential | None:
        response = self._table.get_item(Key={"id": client_id})
        if "Item" in response:
            return ServiceCredential(**response["Item"])
        return None
