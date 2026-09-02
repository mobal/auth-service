import base64
from typing import Annotated
from urllib.parse import urlencode

from aws_lambda_powertools import Logger
from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.dependencies import get_auth_service, get_jwt_bearer
from app.exceptions import OAuthException
from app.models.grant_type import GrantType
from app.models.jwt import JWTToken
from app.models.request.oauth_token import (
    AuthorizationCodeGrantRequest,
    BaseGrantRequest,
    ClientCredentialsGrantRequest,
    PasswordGrantRequest,
    RefreshTokenGrantRequest,
)
from app.models.response.token import OAuthTokenResponse
from app.services.auth_service import AuthService

logger = Logger()

router = APIRouter()

ERROR_MESSAGE_INVALID_CLIENT = "Invalid client: missing or invalid Authorization header"
ERROR_MESSAGE_UNSUPPORTED_GRANT_TYPE = "Unsupported grant type"
ERROR_MESSAGE_UNSUPPORTED_RESPONSE_TYPE = "Unsupported response type"
WARNING_PASSWORD_GRANT_DEPRECATED = '299 auth-service "The password grant type is deprecated per OAuth 2.1 (RFC 6749 Section 4.3). Migrate to the authorization code grant with PKCE."'


def _parse_authorization_header(authorization: str | None) -> tuple[str, str]:
    logger.debug("Parsing Authorization header for client credentials grant")

    if not authorization or not authorization.startswith("Basic "):
        logger.warning("Missing or invalid Basic Authorization header")
        raise OAuthException(
            ERROR_MESSAGE_INVALID_CLIENT,
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Basic"},
        )
    try:
        decoded = base64.b64decode(authorization[6:], validate=True).decode()
    except ValueError:
        logger.warning("Failed to decode Basic Authorization header")
        raise OAuthException(
            ERROR_MESSAGE_INVALID_CLIENT,
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Basic"},
        )

    client_name, _, client_secret = decoded.partition(":")
    if not client_name or not client_secret:
        logger.warning("Basic Authorization header missing client id or secret")
        raise OAuthException(
            ERROR_MESSAGE_INVALID_CLIENT,
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Basic"},
        )

    logger.debug("Parsed client credentials for client_name=%s", client_name)

    return client_name, client_secret


async def parse_oauth_token_request(request: Request) -> BaseGrantRequest:
    """Parse ``/oauth/token`` form body and return the grant-type-specific model.

    Reads ``grant_type`` from the form first, then dispatches to the
    correct Pydantic model.  Validation errors are converted to OAuth 2.0
    complaint error responses.
    """
    form = dict(await request.form())
    grant_type = form.get("grant_type")

    match grant_type:
        case None:
            raise OAuthException(
                "invalid_request",
                "grant_type is required",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        case GrantType.PASSWORD:
            try:
                return PasswordGrantRequest(**form)
            except ValidationError:
                raise OAuthException(
                    "invalid_request", "username and password are required"
                )

        case GrantType.REFRESH_TOKEN:
            try:
                return RefreshTokenGrantRequest(**form)
            except ValidationError:
                raise OAuthException("invalid_request", "refresh_token is required")

        case GrantType.AUTHORIZATION_CODE:
            try:
                return AuthorizationCodeGrantRequest(**form)
            except ValidationError:
                raise OAuthException(
                    "invalid_request", "code and redirect_uri are required"
                )

        case GrantType.CLIENT_CREDENTIALS:
            return ClientCredentialsGrantRequest(**form)

        case _:
            # RFC 6749 Section 5.2: the `error` field must be a machine-readable
            # code from the registered error-code registry.
            raise OAuthException(
                "unsupported_grant_type", ERROR_MESSAGE_UNSUPPORTED_GRANT_TYPE
            )


def _handle_password_grant(
    body: PasswordGrantRequest, auth_service: AuthService
) -> OAuthTokenResponse:
    logger.warning(
        "Password grant used — this flow is deprecated per OAuth 2.1 (BCP). "
        "Migrate clients to authorization code grant with PKCE.",
        extra={"username": body.username},
    )

    access_token, refresh_token, expires_in, scope = auth_service.login(
        body.username, body.password, body.scope
    )

    return OAuthTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        scope=scope,
    )


def _handle_refresh_token_grant(
    body: RefreshTokenGrantRequest, auth_service: AuthService
) -> OAuthTokenResponse:
    logger.info("Handling refresh_token grant")

    access_token, refresh_token, expires_in, scope = auth_service.refresh(
        body.refresh_token
    )

    return OAuthTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        scope=scope,
    )


def _handle_authorization_code_grant(
    body: AuthorizationCodeGrantRequest, auth_service: AuthService
) -> OAuthTokenResponse:
    logger.info("Handling authorization_code grant")

    access_token, refresh_token, expires_in, scope = auth_service.exchange_code(
        body.code, body.redirect_uri, body.code_verifier
    )

    return OAuthTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        scope=scope,
    )


def _handle_client_credentials_grant(
    request: Request, body: ClientCredentialsGrantRequest, auth_service: AuthService
) -> OAuthTokenResponse:
    logger.info("Handling client_credentials grant")
    authorization = request.headers.get("Authorization")
    client_name, client_secret = _parse_authorization_header(authorization)

    access_token, expires_in, scope = auth_service.client_credentials(
        client_name, client_secret, body.scope
    )

    return OAuthTokenResponse(
        access_token=access_token,
        expires_in=expires_in,
        scope=scope,
    )


@router.post(
    "/oauth/token",
    status_code=status.HTTP_200_OK,
)
def token(
    request: Request,
    body: Annotated[BaseGrantRequest, Depends(parse_oauth_token_request)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    logger.info(
        "OAuth token endpoint called",
        extra={"grant_type": str(body.grant_type)},
    )
    match body:
        case PasswordGrantRequest():
            token_response = _handle_password_grant(body, auth_service)
        case RefreshTokenGrantRequest():
            token_response = _handle_refresh_token_grant(body, auth_service)
        case AuthorizationCodeGrantRequest():
            token_response = _handle_authorization_code_grant(body, auth_service)
        case ClientCredentialsGrantRequest():
            token_response = _handle_client_credentials_grant(
                request, body, auth_service
            )

    headers: dict[str, str] = {
        "Cache-Control": "no-store",
        "Pragma": "no-cache",
    }
    if isinstance(body, PasswordGrantRequest):
        headers["Warning"] = WARNING_PASSWORD_GRANT_DEPRECATED

    return JSONResponse(
        content=token_response.model_dump(exclude_none=True),
        status_code=status.HTTP_200_OK,
        headers=headers,
    )


@router.post("/oauth/revoke", status_code=status.HTTP_200_OK)
def revoke(
    jwt_token: Annotated[JWTToken, Depends(get_jwt_bearer)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    logger.info("OAuth token revoke endpoint called for jti=%s", jwt_token.jti)
    auth_service.logout(jwt_token)


@router.get("/oauth/authorize")
def authorize(
    jwt_token: Annotated[JWTToken, Depends(get_jwt_bearer)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    response_type: str = ...,
    client_id: str = ...,
    redirect_uri: str = ...,
    scope: str | None = None,
    state: str | None = None,
    code_challenge: str | None = None,
    code_challenge_method: str | None = None,
) -> Response:
    logger.info(
        "OAuth authorize endpoint called for user_id=%s",
        jwt_token.sub,
        extra={
            "client_id": client_id,
            "user_id": jwt_token.sub,
            "has_scope": scope is not None,
        },  # noqa
    )
    if response_type != "code":
        logger.warning(
            "Unsupported authorize response type",
            extra={"response_type": response_type},
        )
        raise OAuthException(ERROR_MESSAGE_UNSUPPORTED_RESPONSE_TYPE)

    code = auth_service.authorize(
        user_id=jwt_token.sub,
        client_id=client_id,
        redirect_uri=redirect_uri,
        requested_scope=scope,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
    )

    query_params = {"code": code}
    if state:
        query_params["state"] = state

    logger.info(
        "OAuth authorize completed for user_id=%s",
        jwt_token.sub,
        extra={"client_id": client_id, "user_id": jwt_token.sub},  # noqa
    )

    return Response(
        status_code=status.HTTP_302_FOUND,
        headers={"Location": f"{redirect_uri}?{urlencode(query_params)}"},
    )
