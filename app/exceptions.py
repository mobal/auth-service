from typing import Any

from fastapi import HTTPException, status


class AlreadyExistsException(HTTPException):
    def __init__(self, detail: Any):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class InvalidCredentialsException(HTTPException):
    def __init__(self, detail: Any):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class NotFoundException(HTTPException):
    def __init__(self, detail: Any):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class OAuthException(HTTPException):
    def __init__(
        self,
        error: str,
        error_description: str | None = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        headers: dict | None = None,
    ):
        super().__init__(status_code=status_code, detail=error, headers=headers)
        self.oauth_error = error
        self.oauth_error_description = error_description


class TokenExpiredException(HTTPException):
    def __init__(self, detail: Any):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class TokenMismatchException(HTTPException):
    def __init__(self, detail: Any):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class TokenNotFoundException(NotFoundException):
    pass


class UserNotFoundException(NotFoundException):
    pass
