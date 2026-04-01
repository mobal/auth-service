import functools

from aws_lambda_powertools import Logger
from fastapi import HTTPException, status

logger = Logger()


def require_scope(required_scopes: list[str], token_param: str = "jwt_token"):
    logger.debug(
        "Configuring scope requirement",
        extra={"required_scopes": required_scopes, "token_param": token_param},
    )

    def decorator_wrapper(func):
        logger.debug(f"Applying scope decorator to function={func.__name__}")

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

            logger.debug(
                "Token satisfies required scopes",
                extra={"required_scopes": required_scopes},
            )

            return func(*args, **kwargs)

        return wrapper

    return decorator_wrapper
