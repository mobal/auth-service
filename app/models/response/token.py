from pydantic import BaseModel


class OAuthTokenResponse(BaseModel):
    """OAuth 2.0 token endpoint success response (RFC 6749 Section 5.1).

    Returned with HTTP 200 when a token request is successful.
    The client uses ``access_token`` to authenticate API requests and
    ``refresh_token`` (if provided) to obtain new access tokens later.
    """

    access_token: str
    """The issued access token (a JWT string)."""
    token_type: str = "Bearer"
    """Token type — always ``\"Bearer\"`` (RFC 6750 Section 2.1)."""
    expires_in: int
    """Lifetime of the access token in seconds (RFC 6749 Section 5.1)."""
    refresh_token: str | None = None
    """Token used to obtain a new access token without re-authentication."""
    scope: str | None = None
    """Space-separated scope string actually granted."""
