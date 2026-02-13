import pytest
from fastapi.testclient import TestClient
from fastapi import status


class TestRateLimitingMiddleware:

    @pytest.fixture
    def test_client_with_rate_limiting(
        self, initialize_tokens_table, initialize_users_table, monkeypatch
    ) -> TestClient:
        monkeypatch.setattr("app.settings.rate_limiting", True)
        monkeypatch.setattr("app.settings.rate_limit_requests", 5)
        monkeypatch.setattr("app.settings.rate_limit_duration_in_seconds", 60)

        from app.api_handler import app
        from app.middlewares import clients

        clients.clear()

        return TestClient(app, raise_server_exceptions=True)

    @pytest.fixture
    def test_client_without_rate_limiting(
        self, initialize_tokens_table, initialize_users_table, monkeypatch
    ) -> TestClient:
        monkeypatch.setattr("app.settings.rate_limiting", False)

        from app.api_handler import app

        return TestClient(app, raise_server_exceptions=True)

    def test_rate_limiting_disabled_allows_unlimited_requests(
        self, login_url: str, password: str, test_client_without_rate_limiting: TestClient
    ):
        for _ in range(10):
            response = test_client_without_rate_limiting.post(
                login_url,
                json={"email": "root@netcode.hu", "password": password},
            )
            assert response.status_code == status.HTTP_200_OK

    def test_rate_limit_headers_present_in_response(
        self, login_url: str, password: str, test_client_with_rate_limiting: TestClient
    ):
        response = test_client_with_rate_limiting.post(
            login_url,
            json={"email": "root@netcode.hu", "password": password},
        )

        assert response.status_code == status.HTTP_200_OK
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
        assert response.headers["X-RateLimit-Limit"] == "5"
        assert response.headers["X-RateLimit-Remaining"] == "4"

    def test_rate_limit_remaining_decreases_with_requests(
        self, login_url: str, password: str, test_client_with_rate_limiting: TestClient
    ):
        for i in range(1, 4):
            response = test_client_with_rate_limiting.post(
                login_url,
                json={"email": "root@netcode.hu", "password": password},
            )

            assert response.status_code == status.HTTP_200_OK
            remaining = int(response.headers["X-RateLimit-Remaining"])
            assert remaining == 5 - i

    def test_rate_limit_exceeded_returns_429(
        self, login_url: str, password: str, test_client_with_rate_limiting: TestClient
    ):
        # Make 5 requests (the limit)
        for _ in range(5):
            response = test_client_with_rate_limiting.post(
                login_url,
                json={"email": "root@netcode.hu", "password": password},
            )
            assert response.status_code == status.HTTP_200_OK

        response = test_client_with_rate_limiting.post(
            login_url,
            json={"email": "root@netcode.hu", "password": password},
        )

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "Rate limit exceeded" in response.json()["message"]

    def test_rate_limit_headers_on_429_response(
        self, login_url: str, password: str, test_client_with_rate_limiting: TestClient
    ):
        # Make requests until rate limit is exceeded
        for _ in range(5):
            test_client_with_rate_limiting.post(
                login_url,
                json={"email": "root@netcode.hu", "password": password},
            )

        response = test_client_with_rate_limiting.post(
            login_url,
            json={"email": "root@netcode.hu", "password": password},
        )

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
        assert response.headers["X-RateLimit-Remaining"] == "0"

    def test_rate_limit_reset_after_window(
        self, login_url: str, password: str, test_client_with_rate_limiting: TestClient, monkeypatch
    ):
        from app.middlewares import clients
        from datetime import datetime, timedelta

        # Make 5 requests to hit the limit
        for _ in range(5):
            test_client_with_rate_limiting.post(
                login_url,
                json={"email": "root@netcode.hu", "password": password},
            )

        response = test_client_with_rate_limiting.post(
            login_url,
            json={"email": "root@netcode.hu", "password": password},
        )
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

        client_ip = list(clients.keys())[0]
        clients[client_ip]["last_request"] = datetime.now() - timedelta(seconds=61)

        response = test_client_with_rate_limiting.post(
            login_url,
            json={"email": "root@netcode.hu", "password": password},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["X-RateLimit-Remaining"] == "4"

    def test_rate_limit_per_client_ip(
        self, initialize_tokens_table, initialize_users_table, login_url: str, monkeypatch, password: str
    ):
        monkeypatch.setattr("app.settings.rate_limiting", True)
        monkeypatch.setattr("app.settings.rate_limit_requests", 2)
        monkeypatch.setattr("app.settings.rate_limit_duration_in_seconds", 60)

        from app.api_handler import app
        from app.middlewares import clients

        clients.clear()

        test_client = TestClient(app, raise_server_exceptions=True)

        for _ in range(2):
            response = test_client.post(
                login_url,
                json={"email": "root@netcode.hu", "password": password},
            )
            assert response.status_code == status.HTTP_200_OK

        response = test_client.post(
            login_url,
            json={"email": "root@netcode.hu", "password": password},
        )
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

