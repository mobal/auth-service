from aws_lambda_powertools import Logger
from fastapi import Form
from pydantic import BaseModel

logger = Logger()


class OAuthTokenRequest(BaseModel):
    """OAuth 2.0 token endpoint request (RFC 6749 Section 4.1.3).

    Accepted as an ``application/x-www-form-urlencoded`` POST body.
    Which fields are required depends on ``grant_type``:

    * ``authorization_code`` — ``code``, ``redirect_uri``, ``code_verifier``
    * ``password`` — ``username``, ``password``
    * ``refresh_token`` — ``refresh_token``
    * ``client_credentials`` — no additional fields
    """

    grant_type: str
    """OAuth 2.0 grant type (see :class:`~app.models.grant_type.GrantType`)."""
    username: str | None = None
    """Resource owner username (``password`` grant only)."""
    password: str | None = None
    """Resource owner password (``password`` grant only)."""
    refresh_token: str | None = None
    """Refresh token value (``refresh_token`` grant only)."""
    code: str | None = None
    """Authorization code value (``authorization_code`` grant only)."""
    code_verifier: str | None = None
    """PKCE code verifier (RFC 7636 Section 4.1)."""
    redirect_uri: str | None = None
    """Redirect URI sent in the original authorization request."""
    scope: str | None = None
    """Space-separated list of requested permission scopes."""

    @classmethod
    def as_form(
        cls,
        grant_type: str = Form(...),
        username: str | None = Form(None),
        password: str | None = Form(None),
        refresh_token: str | None = Form(None),
        code: str | None = Form(None),
        code_verifier: str | None = Form(None),
        redirect_uri: str | None = Form(None),
        scope: str | None = Form(None),
    ) -> "OAuthTokenRequest":
        logger.debug(
            "Building OAuthTokenRequest from form data",
            extra={"grant_type": grant_type},
        )
        return cls(
            grant_type=grant_type,
            username=username,
            password=password,
            refresh_token=refresh_token,
            code=code,
            code_verifier=code_verifier,
            redirect_uri=redirect_uri,
            scope=scope,
        )
