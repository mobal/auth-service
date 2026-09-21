import time
from threading import Lock
from urllib.parse import urlencode, urljoin

import httpx2 as httpx
from aws_lambda_powertools import Logger

from app import settings
from app.clients.circuit_breaker import create_circuit_breaker
from app.models.google_oidc_provider import GoogleOIDCProviderMetadata


class GoogleOIDCClient:
    """Server-side client for Google's OpenID Connect endpoints."""

    _metadata_cache: GoogleOIDCProviderMetadata | None = None
    _metadata_expires_at = 0.0
    _metadata_lock = Lock()

    def __init__(self) -> None:
        self._logger = Logger()
        self._client = httpx.Client(timeout=httpx.Timeout(10.0))
        self._breaker = create_circuit_breaker("google-oidc")

    def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make a request and count transport and upstream-server failures."""
        if method == "GET":
            response = self._client.get(url, **kwargs)
        elif method == "POST":
            response = self._client.post(url, **kwargs)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        if response.status_code >= 500:
            response.raise_for_status()
        return response

    def get_metadata(self) -> GoogleOIDCProviderMetadata:
        now = time.monotonic()
        if self._metadata_cache is not None and now < self._metadata_expires_at:
            return self._metadata_cache

        with self._metadata_lock:
            now = time.monotonic()
            if self._metadata_cache is not None and now < self._metadata_expires_at:
                return self._metadata_cache

            discovery_url = urljoin(
                f"{settings.google_oidc_issuer.rstrip('/')}/",
                ".well-known/openid-configuration",
            )
            response = self._breaker.call(self._request, "GET", discovery_url)
            response.raise_for_status()
            metadata = GoogleOIDCProviderMetadata.model_validate(response.json())
            if str(metadata.issuer).rstrip("/") != settings.google_oidc_issuer.rstrip(
                "/"
            ):
                raise ValueError("Google OIDC discovery returned an unexpected issuer")
            self._metadata_cache = metadata
            self._metadata_expires_at = now + 3600
            return metadata

    def authorization_url(self, state: str, nonce: str) -> str:
        metadata = self.get_metadata()
        params = {
            "response_type": "code",
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "scope": "openid email profile",
            "state": state,
            "nonce": nonce,
        }
        return f"{metadata.authorization_endpoint}?{urlencode(params)}"

    def exchange_code(self, code: str) -> dict:
        metadata = self.get_metadata()
        response = self._breaker.call(
            self._request,
            "POST",
            str(metadata.token_endpoint),
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
            },
        )
        response.raise_for_status()
        return response.json()
