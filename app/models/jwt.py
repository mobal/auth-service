from typing import Any

from pydantic import BaseModel


class JWTToken(BaseModel):
    """JWT access token payload conforming to RFC 7519 Section 4.1.

    Represents the decoded claims carried in an OAuth 2.0 access token JWT.
    All standard registered claims are optional per RFC 7519, but OAuth 2.0
    usage requires ``iss``, ``exp``, ``sub``, and ``jti`` for security.
    """

    exp: int
    """Expiration time (Unix timestamp, RFC 7519 Section 4.1.4)."""
    iat: int
    """Issued-at time (Unix timestamp, RFC 7519 Section 4.1.6)."""
    iss: str | None = None
    """Issuer identifier (RFC 7519 Section 4.1.1)."""
    aud: str | list[str] | None = None
    """Audience — single string or array of strings (RFC 7519 Section 4.1.3)."""
    jti: str
    """Unique token identifier for replay detection (RFC 7519 Section 4.1.7)."""
    sub: Any
    """Subject — the principal the token represents (RFC 7519 Section 4.1.2)."""
    scope: str | None = None
    """Space-separated OAuth 2.0 scope string."""


class RefreshToken(BaseModel):
    """OAuth 2.0 refresh token value and metadata (RFC 6749 Section 1.5).

    Used to obtain a new access token without requiring the resource owner
    to re-authenticate.  Stored server-side for rotation and revocation.
    """

    token: str
    """The opaque refresh token string."""
    ttl: int
    """Time-to-live in seconds (Unix timestamp of expiry)."""
