from pydantic import BaseModel


class OAuthAuthorizeRequest(BaseModel):
    """OAuth 2.0 authorization endpoint request (RFC 6749 Section 4.1.1).

    The resource owner's user-agent redirects to this endpoint with
    these query-string parameters to initiate an authorization code grant.
    Browser/public-client requests require PKCE with S256 (RFC 7636 Section 4).
    """  # noqa: E501

    response_type: str
    """Must be ``\"code\"`` for the authorization code grant flow."""
    client_id: str
    """The requesting client's identifier (RFC 6749 Section 2.3.1)."""
    redirect_uri: str
    """URI the user-agent is redirected to after authorization."""
    scope: str | None = None
    """Space-separated list of requested permission scopes."""
    state: str | None = None
    """Opaque value for CSRF protection (RFC 6749 Section 4.1.1)."""
    code_challenge: str | None = None
    """PKCE code challenge; required for browser/public clients."""
    code_challenge_method: str | None = None
    """PKCE challenge method; browser/public clients must use ``\"S256\"``."""
