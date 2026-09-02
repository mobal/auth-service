from pydantic import BaseModel, Field


class BaseGrantRequest(BaseModel):
    """Fields common to all OAuth 2.0 token grant types.

    Accepted as an ``application/x-www-form-urlencoded`` POST body.
    """

    scope: str | None = None
    """Space-separated list of requested permission scopes."""


class PasswordGrantRequest(BaseGrantRequest):
    """Resource owner password credentials grant (RFC 6749 Section 4.3)."""

    grant_type: str = Field(min_length=1)
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class RefreshTokenGrantRequest(BaseGrantRequest):
    """Refresh token grant (RFC 6749 Section 6)."""

    grant_type: str = Field(min_length=1)
    refresh_token: str = Field(min_length=1)


class AuthorizationCodeGrantRequest(BaseGrantRequest):
    """Authorization code grant (RFC 6749 Section 4.1)."""

    grant_type: str = Field(min_length=1)
    code: str = Field(min_length=1)
    redirect_uri: str = Field(min_length=1)
    code_verifier: str | None = None


class ClientCredentialsGrantRequest(BaseGrantRequest):
    """Client credentials grant (RFC 6749 Section 4.4)."""

    grant_type: str = Field(min_length=1)
