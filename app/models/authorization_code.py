from pydantic import BaseModel


class AuthorizationCode(BaseModel):
    """OAuth 2.0 authorization code with PKCE support (RFC 6749 Section 4.1, RFC 7636).

    Issued by the authorization endpoint upon successful resource-owner
    authentication.  Must be single-use (consumed flag) and short-lived (ttl).
    PKCE fields are populated when the authorization request included
    code_challenge and code_challenge_method (RFC 7636 Section 4).
    """

    id: str
    """Internal primary key (UUID)."""
    code: str
    """The authorization code value sent to the client."""
    client_id: str
    """The client that requested this authorization code."""
    user_id: str
    """The authenticated resource owner."""
    redirect_uri: str
    """Redirect URI the client registered — must match at token exchange."""
    scope: str | None = None
    """Space-separated scope string granted to the authorization code."""
    code_challenge: str | None = None
    """PKCE code challenge from the authorization request (RFC 7636 Section 4.2)."""
    code_challenge_method: str | None = None
    """PKCE challenge method — ``"S256"`` or ``"plain"`` (RFC 7636 Section 4.2)."""
    ttl: int
    """Time-to-live in seconds (Unix timestamp of expiry)."""
    consumed: bool = False
    """Whether this code has already been consumed (single-use enforcement)."""
