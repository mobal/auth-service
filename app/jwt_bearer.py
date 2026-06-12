import jwt
from aws_lambda_powertools import Logger
from fastapi import HTTPException, Request, status
from fastapi.security.http import (
    HTTPAuthorizationCredentials,
    HTTPBearer as FastAPIHTTPBearer,
)
from fastapi.security.utils import get_authorization_scheme_param
from jwt import DecodeError, ExpiredSignatureError
from pydantic import ValidationError

from app import settings
from app.models.jwt import JWTToken
from app.services.token_service import TokenService

logger = Logger(utc=True)

ERROR_MESSAGE_NOT_AUTHENTICATED = "Not authenticated"


class HTTPBearer(FastAPIHTTPBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
        self._auto_error = auto_error
        logger.debug("HTTPBearer initialized")

    def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None:
        logger.debug(
            "Resolving HTTP authorization credentials",
            extra={"path": request.url.path, "method": request.method},
        )
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
            logger.warning("Missing authorization, scheme or credentials")

            if self._auto_error:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=ERROR_MESSAGE_NOT_AUTHENTICATED,
                )
            else:
                return None
        if scheme.lower() != "bearer":
            logger.warning("Invalid scheme=%s", scheme)

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
            logger.warning("Missing token in query parameter fallback")
            if self._auto_error:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=ERROR_MESSAGE_NOT_AUTHENTICATED,
                )
            else:
                return None

        logger.debug("Using token from query parameter fallback")
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


class JWTBearer:
    def __init__(
        self, auto_error: bool = True, token_service: TokenService | None = None
    ):
        self._auto_error = auto_error
        self._http_bearer = HTTPBearer(auto_error=auto_error)
        self._token_service = token_service
        logger.debug("JWTBearer initialized")

    def __call__(self, request: Request) -> JWTToken | None:
        logger.debug("Validating bearer token from request")
        credentials = self._http_bearer.__call__(request)
        if credentials:
            decoded_token = self._validate_token(credentials.credentials)
            if decoded_token is None:
                if self._auto_error:
                    logger.warning("Invalid authentication token")

                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=ERROR_MESSAGE_NOT_AUTHENTICATED,
                    )

                return None

            return decoded_token

        return None

    def _validate_token(self, token: str) -> JWTToken | None:
        try:
            decoded_token = JWTToken(
                **jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
            )
            if self._token_service.get_by_id(decoded_token.jti):
                logger.debug(
                    "Token accepted for jti=%s",
                    decoded_token.jti,
                    extra={"sub": decoded_token.sub},
                )

                return decoded_token
            logger.debug("Token rejected (blacklisted) jti=%s", decoded_token.jti)
        except DecodeError as err:
            logger.exception("Error occurred during token decoding: %s", err)
        except ExpiredSignatureError as err:
            logger.exception("Expired signature: %s", err)
        except ValidationError as err:
            logger.exception("Invalid JWT payload structure: %s", err)

        return None
