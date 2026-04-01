import uuid

import pendulum

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
