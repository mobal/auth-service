from app.models.audience import Audience
from app.repositories.audience_repository import AudienceRepository


class TestAudienceRepository:
    def test_get_by_audience_returns_registered_audience(
        self, audiences_table, audience_item: dict
    ):
        repository = AudienceRepository()

        result = repository.get_by_audience(audience_item["audience"])

        assert result == Audience(**audience_item)

    def test_get_by_audience_returns_none_for_unregistered_audience(
        self, audiences_table
    ):
        repository = AudienceRepository()

        result = repository.get_by_audience("missing-audience")

        assert result is None

    def test_create_persists_audience(self, audiences_table, audience_item: dict):
        audiences_table.delete_item(Key={"audience": audience_item["audience"]})
        repository = AudienceRepository()

        repository.create(audience_item)

        result = repository.get_by_audience(audience_item["audience"])
        assert result == Audience(**audience_item)
