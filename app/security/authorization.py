from functools import wraps

from fastapi import HTTPException, status


def pre_authorize(required_role: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from app.api.v1.routers.auth_router import jwt_bearer

            if (
                not hasattr(jwt_bearer, "decoded_token")
                or jwt_bearer.decoded_token is None
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="Not authenticated"
                )

            user_data = jwt_bearer.decoded_token.user
            roles = user_data.get("roles", [])

            if required_role not in roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions",
                )

            return func(*args, **kwargs)

        return wrapper

    return decorator
