import functools

from aws_lambda_powertools import Logger
from fastapi import HTTPException, status

logger = Logger()


def require_scope(required_scopes: list[str], token_param: str = "jwt_token"):
    def decorator_wrapper(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            token = kwargs.get(token_param)
            token_scopes = set(token.scope.split()) if token.scope else set()

            if not any(scope in token_scopes for scope in required_scopes):
                logger.warning(
                    "Token does not have required scopes: %s", required_scopes
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient scope",
                )

            return func(*args, **kwargs)

        return wrapper

    return decorator_wrapper
