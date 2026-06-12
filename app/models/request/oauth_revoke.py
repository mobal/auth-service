from aws_lambda_powertools import Logger
from fastapi import Form
from pydantic import BaseModel

logger = Logger()


class OAuthRevokeRequest(BaseModel):
    """OAuth 2.0 token revocation request (RFC 7009 Section 2.1).

    Sent by clients to the revocation endpoint to invalidate a specific
    access or refresh token.  The server responds with HTTP 200 regardless
    of whether the token was known (to avoid leaking token validity).
    """

    token: str
    """The token string to revoke (access or refresh token)."""

    @classmethod
    def as_form(cls, token: str = Form(...)) -> "OAuthRevokeRequest":
        logger.debug("Building OAuthRevokeRequest from form data")
        return cls(token=token)
