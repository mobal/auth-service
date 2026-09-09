from app.models.models import CamelModel


class RoleScope(CamelModel):
    """Role-to-scope mapping persisted in the ``role-scopes`` table.

    Each item maps a single role name to the OAuth 2.0 scopes that are
    granted to tokens whose owner carries that role.  Used by
    :meth:`AuthService._derive_scope` instead of a hard-coded map so that
    role permissions can be managed without a redeploy.
    """

    role: str
    """Role name as stored on the user document (e.g. ``root``)."""
    scopes: list[str] = []
    """OAuth 2.0 scopes granted to holders of this role."""
