import json
import secrets
import time
from threading import Lock
from urllib.parse import urlencode, urljoin

import httpx2 as httpx
import jwt
from aws_lambda_powertools import Logger

from app import settings
from app.clients.circuit_breaker import create_circuit_breaker
from app.exceptions import GoogleOIDCValidationError
from app.models.google_identity import GoogleIdentity
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

    def validate_id_token(self, id_token: str, nonce: str) -> GoogleIdentity:
        """Validate Google's signed ID token and return its identity claims."""
        try:
            metadata = self.get_metadata()
            header = jwt.get_unverified_header(id_token)
            key_id = header.get("kid")
            if not key_id or header.get("alg") != "RS256":
                raise GoogleOIDCValidationError("Unsupported Google ID token header")

            jwks_response = self._breaker.call(
                self._request, "GET", str(metadata.jwks_uri)
            )
            jwks_response.raise_for_status()
            jwk = next(
                (
                    key
                    for key in jwks_response.json().get("keys", [])
                    if key.get("kid") == key_id
                ),
                None,
            )
            if jwk is None:
                raise GoogleOIDCValidationError("Google signing key was not found")

            signing_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
            claims = jwt.decode(
                id_token,
                signing_key,
                algorithms=["RS256"],
                audience=settings.google_client_id,
                issuer=settings.google_oidc_issuer,
                options={"require": ["iss", "sub", "aud", "exp", "nonce"]},
            )
            token_nonce = claims.get("nonce")
            if not isinstance(token_nonce, str) or not secrets.compare_digest(
                token_nonce, nonce
            ):
                raise GoogleOIDCValidationError("Google ID token nonce mismatch")

            email = claims.get("email")
            if not isinstance(email, str) or claims.get("email_verified") is not True:
                raise GoogleOIDCValidationError("Google email is not verified")

            return GoogleIdentity(
                issuer=str(claims["iss"]),
                subject=str(claims["sub"]),
                email=email,
                email_verified=True,
                nonce=token_nonce,
            )
        except GoogleOIDCValidationError:
            raise
        except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as error:
            raise GoogleOIDCValidationError("Invalid Google ID token") from error
