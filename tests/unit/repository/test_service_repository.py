import uuid

import pendulum
import pytest
from botocore.exceptions import ClientError

from app.models.service import ServiceCredential
from app.repositories.service_repository import ServiceRepository


class TestServiceRepository:
    def test_successfully_create_service(
        self,
        service_credential: ServiceCredential,
        service_repository: ServiceRepository,
        services_table,
    ):
        service_credential.name = str(uuid.uuid4())
        credential = {
            "id": service_credential.name,
            "secret": service_credential.secret,
            "scopes": service_credential.scopes,
            "created_at": pendulum.now().to_iso8601_string(),
        }
        service_repository.create_service(credential)

        response = services_table.get_item(
            Key={"id": credential["id"]},
        )

        assert response["Item"] == credential

    def test_successfully_get_by_id(
        self,
        service_credential: ServiceCredential,
        service_repository: ServiceRepository,
        services_table,
    ):
        item = service_repository.get_by_id(service_credential.id)

        assert item == service_credential

    def test_get_by_id_returns_none_if_service_not_found(
        self,
        service_repository: ServiceRepository,
        services_table,
    ):
        assert service_repository.get_by_id(str(uuid.uuid4())) is None

    def test_successfully_get_by_name(
        self,
        service_credential: ServiceCredential,
        service_repository: ServiceRepository,
        services_table,
    ):
        item = service_repository.get_by_name("test-service")

        assert item == service_credential

    def test_get_by_name_returns_none_if_service_not_found(
        self,
        service_repository: ServiceRepository,
        services_table,
    ):
        assert service_repository.get_by_name("non-existent-service") is None

    def test_create_service_raises_client_error_on_throttling(
        self,
        mocker,
        service_credential: ServiceCredential,
        service_repository: ServiceRepository,
    ):
        error_response = {
            "Error": {
                "Code": "ProvisionedThroughputExceededException",
                "Message": "Rate exceeded",
            }
        }
        mocker.patch.object(
            service_repository._table,
            "put_item",
            side_effect=ClientError(error_response, "PutItem"),
        )
        with pytest.raises(ClientError):
            service_repository.create_service(
                {
                    "id": str(uuid.uuid4()),
                    "secret": service_credential.secret,
                    "scopes": service_credential.scopes,
                    "created_at": pendulum.now().to_iso8601_string(),
                }
            )

    def test_get_by_id_raises_client_error(
        self,
        mocker,
        service_repository: ServiceRepository,
    ):
        error_response = {
            "Error": {
                "Code": "InternalServerError",
                "Message": "Internal error",
            }
        }
        mocker.patch.object(
            service_repository._table,
            "get_item",
            side_effect=ClientError(error_response, "GetItem"),
        )
        with pytest.raises(ClientError):
            service_repository.get_by_id(str(uuid.uuid4()))

    def test_get_by_name_raises_client_error(
        self,
        mocker,
        service_repository: ServiceRepository,
    ):
        error_response = {
            "Error": {
                "Code": "InternalServerError",
                "Message": "Internal error",
            }
        }
        mocker.patch.object(
            service_repository._table,
            "query",
            side_effect=ClientError(error_response, "Query"),
        )
        with pytest.raises(ClientError):
            service_repository.get_by_name("test-service")

    def test_get_by_id_returns_none_for_empty_id(
        self,
        service_repository: ServiceRepository,
        services_table,
    ):
        with pytest.raises(ClientError):
            service_repository.get_by_id("")

    def test_get_by_name_returns_none_for_empty_name(
        self,
        service_repository: ServiceRepository,
        services_table,
    ):
        with pytest.raises(ClientError):
            service_repository.get_by_name("")

    def test_create_service_with_empty_scopes(
        self,
        service_credential: ServiceCredential,
        service_repository: ServiceRepository,
        services_table,
    ):
        credential = {
            "id": str(uuid.uuid4()),
            "name": "test-empty-scopes",
            "secret": service_credential.secret,
            "scopes": [],
            "created_at": pendulum.now().to_iso8601_string(),
        }
        service_repository.create_service(credential)

        response = services_table.get_item(Key={"id": credential["id"]})

        assert response["Item"] == credential
