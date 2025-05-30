import jwt
from aws_lambda_powertools import Logger
from fastapi import HTTPException, Request, status
from fastapi.security.http import HTTPAuthorizationCredentials
from fastapi.security.http import HTTPBearer as FastAPIHTTPBearer
from fastapi.security.utils import get_authorization_scheme_param
from jwt import DecodeError, ExpiredSignatureError

from app import settings
from app.models import JWTToken
from app.services import TokenService

logger = Logger(utc=True)

ERROR_MESSAGE_NOT_AUTHENTICATED = "Not authenticated"


class HTTPBearer(FastAPIHTTPBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
        self._auto_error = auto_error

    def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None:
        authorization = request.headers.get("Authorization")
        if authorization is not None:
            return self._get_authorization_credentials_from_header(authorization)
        else:
            logger.info(
                "Missing authentication header, attempt to use token query param"
            )
            return self._get_authorization_credentials_from_token(
                request.query_params.get("token")
            )

    def _get_authorization_credentials_from_header(
        self, authorization: str
    ) -> HTTPAuthorizationCredentials | None:
        scheme, credentials = get_authorization_scheme_param(authorization)
        if not (authorization and scheme and credentials):
            logger.warning(f"Missing {authorization=}, {scheme=} or {credentials=}")
            if self._auto_error:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=ERROR_MESSAGE_NOT_AUTHENTICATED,
                )
            else:
                return None
        if scheme.lower() != "bearer":
            logger.warning(f"Invalid {scheme=}")
            if self._auto_error:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid authentication credentials",
                )
            else:
                return None
        return HTTPAuthorizationCredentials(scheme=scheme, credentials=credentials)

    def _get_authorization_credentials_from_token(
        self, token: str | None
    ) -> HTTPAuthorizationCredentials | None:
        if not token:
            if self._auto_error:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=ERROR_MESSAGE_NOT_AUTHENTICATED,
                )
            else:
                return None
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


class JWTBearer:
    def __init__(self, auto_error: bool = True):
        self._auto_error = auto_error
        self._token_service = TokenService()

    def __call__(self, request: Request) -> JWTToken | None:
        credentials = HTTPBearer(self._auto_error).__call__(request)
        if credentials:
            if not self._validate_token(credentials.credentials):
                if self._auto_error:
                    logger.warning(f"Invalid authentication token {credentials=}")
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=ERROR_MESSAGE_NOT_AUTHENTICATED,
                    )
                else:
                    return None
            return self.decoded_token
        else:
            return None

    def _validate_token(self, token: str) -> bool:
        try:
            decoded_token = JWTToken(
                **jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
            )
            if self._token_service.get_by_id(decoded_token.jti):
                logger.debug(f"Token is not blacklisted {decoded_token=}")
                self.decoded_token = decoded_token
                return True
            logger.debug(f"Token blacklisted {decoded_token=}")
        except DecodeError as err:
            logger.exception(f"Error occurred during token decoding {err=}")
        except ExpiredSignatureError as err:
            logger.exception(f"Expired signature {err=}")
        return False
