from enum import StrEnum, auto


class GrantType(StrEnum):
    PASSWORD = auto()
    REFRESH_TOKEN = auto()
    CLIENT_CREDENTIALS = auto()
    AUTHORIZATION_CODE = auto()
