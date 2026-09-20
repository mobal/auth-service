from app.repositories.google_oidc_state_repository import GoogleOIDCStateRepository


class TestGoogleOIDCStateRepository:
    def test_create_get_and_consume_state(self, initialize_google_oidc_states_table):
        repository = GoogleOIDCStateRepository()

        created = repository.create("pending-request", lifetime_seconds=600)

        assert repository.get(created.state) == created
        assert repository.consume(created.state) == created
        assert repository.get(created.state) is None
        assert repository.consume(created.state) is None

    def test_get_returns_none_for_unknown_state(
        self, initialize_google_oidc_states_table
    ):
        repository = GoogleOIDCStateRepository()

        assert repository.get("unknown-state") is None
