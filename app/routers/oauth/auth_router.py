import base64
from typing import Annotated
from urllib.parse import urlencode

from aws_lambda_powertools import Logger
from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse

from app.dependencies import get_auth_service, get_jwt_bearer
from app.exceptions import OAuthException
from app.models.grant_type import GrantType
from app.models.jwt import JWTToken
from app.models.request.oauth_token import OAuthTokenRequest
from app.models.response.token import OAuthTokenResponse
from app.services.auth_service import AuthService

logger = Logger()

router = APIRouter()

ERROR_MESSAGE_INVALID_CLIENT = "Invalid client: missing or invalid Authorization header"
ERROR_MESSAGE_UNSUPPORTED_GRANT_TYPE = "Unsupported grant type"


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
    except Exception:
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


def _handle_password_grant(
    body: OAuthTokenRequest, auth_service: AuthService
) -> OAuthTokenResponse:
    logger.info("Handling password grant")
    if not body.username or not body.password:
        logger.warning("Password grant is missing username or password")
        raise OAuthException("Invalid request: username and password are required")

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
    body: OAuthTokenRequest, auth_service: AuthService
) -> OAuthTokenResponse:
    logger.info("Handling refresh_token grant")
    if not body.refresh_token:
        logger.warning("Refresh token grant is missing refresh_token")
        raise OAuthException("Invalid request: refresh_token is required")

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
    body: OAuthTokenRequest, auth_service: AuthService
) -> OAuthTokenResponse:
    logger.info("Handling authorization_code grant")
    if not body.code or not body.redirect_uri:
        logger.warning("Authorization code grant is missing code or redirect_uri")
        raise OAuthException("Invalid request: code and redirect_uri are required")

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
    request: Request, body: OAuthTokenRequest, auth_service: AuthService
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
    body: Annotated[OAuthTokenRequest, Depends(OAuthTokenRequest.as_form)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    logger.info(
        "OAuth token endpoint called",
        extra={"grant_type": str(body.grant_type)},
    )
    match body.grant_type:
        case GrantType.PASSWORD:
            token_response = _handle_password_grant(body, auth_service)
        case GrantType.REFRESH_TOKEN:
            token_response = _handle_refresh_token_grant(body, auth_service)
        case GrantType.AUTHORIZATION_CODE:
            token_response = _handle_authorization_code_grant(body, auth_service)
        case GrantType.CLIENT_CREDENTIALS:
            token_response = _handle_client_credentials_grant(
                request, body, auth_service
            )
        case _:
            logger.warning("Unsupported grant type received")
            raise OAuthException(ERROR_MESSAGE_UNSUPPORTED_GRANT_TYPE)

    return JSONResponse(
        content=token_response.model_dump(exclude_none=True),
        status_code=status.HTTP_200_OK,
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
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
        extra={"client_id": client_id, "user_id": jwt_token.sub, "has_scope": scope is not None},
    )
    if response_type != "code":
        logger.warning(
            "Unsupported authorize response type",
            extra={"response_type": response_type},
        )
        raise OAuthException(ERROR_MESSAGE_UNSUPPORTED_GRANT_TYPE)

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
        extra={"client_id": client_id, "user_id": jwt_token.sub},
    )

    return Response(
        status_code=status.HTTP_302_FOUND,
        headers={"Location": f"{redirect_uri}?{urlencode(query_params)}"},
    )
