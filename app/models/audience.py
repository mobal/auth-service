from app.models.models import CamelModel


class Audience(CamelModel):
    """Registered audience in the DynamoDB-backed audience registry.

    The registry is the single source of truth for which audiences exist
    and which clients are allowed to request tokens for them.  When a
    client requests an ``audience`` at the token endpoint, the audience
    must be registered here and the client must be listed in
    ``allowed_clients`` before the JWT ``aud`` claim is set
    (RFC 7519 Section 4.1.3).
    """

    audience: str
    """The audience identifier value placed in the JWT ``aud`` claim."""
    allowed_clients: list[str] = []
    """Client names permitted to request tokens for this audience."""
    created_at: str
    """ISO 8601 timestamp of when this audience was registered."""
