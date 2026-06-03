from app.models.models import CamelModel


class ServiceCredential(CamelModel):
    """OAuth 2.0 client credential (service account) registration.

    Used for the ``client_credentials`` grant type (RFC 6749 Section 4.4).
    Each credential has a unique name and a secret used for authentication
    at the token endpoint.  The ``scopes`` list defines which permissions
    are granted to tokens issued under this credential.
    """

    id: str
    """Internal primary key (UUID)."""
    name: str
    """Human-readable client identifier."""
    secret: str
    """Client secret used to authenticate at the token endpoint."""
    scopes: list[str] = []
    """List of OAuth 2.0 scopes this credential is authorized for."""
    created_at: str
    """ISO 8601 timestamp of when this credential was created."""
