import boto3
from aws_lambda_powertools import Logger

from app import settings
from app.models.role_scope import RoleScope


class RoleScopeRepository:
    """Reads role-to-scope mappings from the ``role-scopes`` table."""

    def __init__(self) -> None:
        self._logger = Logger()
        self._table = (
            boto3.Session().resource("dynamodb").Table(
                f"{settings.stage}-{settings.app_name}-role-scopes"
            )
        )

    def get_by_roles(self, roles: list[str]) -> dict[str, list[str]]:
        """Return a ``role -> scopes`` mapping for the requested roles.

        Roles without a stored mapping are simply absent from the result.
        """
        if not roles:
            return {}

        self._logger.debug(
            "Fetching role-scope mappings",
            extra={"roles_count": len(roles)},
        )
        mapping: dict[str, list[str]] = {}
        for role in set(roles):
            response = self._table.get_item(Key={"role": role})
            if "Item" not in response:
                continue
            role_scope = RoleScope(**response["Item"])
            mapping[role_scope.role] = role_scope.scopes

        missing = set(roles) - set(mapping)
        if missing:
            self._logger.warning(
                "No scope mapping stored for roles",
                extra={"missing_roles": sorted(missing)},
            )
        return mapping
