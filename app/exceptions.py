from typing import Any

from fastapi import HTTPException, status


class NotFoundException(HTTPException):
    def __init__(self, detail):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class UserNotFoundException(NotFoundException):
    pass


class TokenMistmatchException(HTTPException):
    def __init__(self, detail: Any):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail
        )


class TokenNotFoundException(NotFoundException):
    pass
