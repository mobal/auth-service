from typing import Any

from fastapi import HTTPException, status


class AlreadyExistsException(HTTPException):
    def __init__(self, detail: Any):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class NotFoundException(HTTPException):
    def __init__(self, detail: Any):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class UserNotFoundException(NotFoundException):
    pass


class TokenExpiredException(HTTPException):
    def __init__(self, detail: Any):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class TokenMismatchException(HTTPException):
    def __init__(self, detail: Any):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class TokenNotFoundException(NotFoundException):
    pass


class UserAlreadyExistsException(AlreadyExistsException):
    pass
