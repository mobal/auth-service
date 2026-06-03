from enum import StrEnum, auto


class GrantType(StrEnum):
    """OAuth 2.0 grant type constants (RFC 6749 Sections 1.3, 4.1, 4.3, 4.4, 6).

    Used in token endpoint requests to identify the authorization grant
    the client is using.  Each value corresponds to a specific grant flow.
    """

    PASSWORD = auto()
    """Resource owner password credentials grant (RFC 6749 Section 4.3)."""
    REFRESH_TOKEN = auto()
    """Refresh token grant (RFC 6749 Section 6)."""
    CLIENT_CREDENTIALS = auto()
    """Client credentials grant (RFC 6749 Section 4.4)."""
    AUTHORIZATION_CODE = auto()
    """Authorization code grant (RFC 6749 Section 4.1)."""
