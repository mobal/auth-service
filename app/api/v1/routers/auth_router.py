import base64
from typing import Annotated
from urllib.parse import urlencode

from aws_lambda_powertools import Logger
from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse

from app.exceptions import OAuthException
from app.jwt_bearer import JWTBearer
from app.models.grant_type import GrantType
from app.models.jwt import JWTToken
from app.models.request.oauth_token import OAuthTokenRequest
from app.models.request.register import RegistrationRequest
from app.models.response.token import OAuthTokenResponse
from app.security.authorization import require_scope
from app.services.auth_service import AuthService
from app.services.user_service import UserService

logger = Logger()

auth_service = AuthService()
jwt_bearer = JWTBearer()
router = APIRouter()
user_service = UserService()


ERROR_MESSAGE_INVALID_CLIENT = "Invalid client: missing or invalid Authorization header"
ERROR_MESSAGE_UNSUPPORTED_GRANT_TYPE = "Unsupported grant type"


def _parse_authorization_header(authorization: str | None) -> tuple[str, str]:
    if not authorization or not authorization.startswith("Basic "):
        raise OAuthException(
            ERROR_MESSAGE_INVALID_CLIENT,
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Basic"},
        )
    try:
        decoded = base64.b64decode(authorization[6:], validate=True).decode()
    except Exception:
        raise OAuthException(
            ERROR_MESSAGE_INVALID_CLIENT,
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Basic"},
        )

    client_id, _, client_secret = decoded.partition(":")
    if not client_id or not client_secret:
        raise OAuthException(
            ERROR_MESSAGE_INVALID_CLIENT,
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Basic"},
        )

    return client_id, client_secret


def _handle_password_grant(body: OAuthTokenRequest) -> OAuthTokenResponse:
    if not body.username or not body.password:
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


def _handle_refresh_token_grant(body: OAuthTokenRequest) -> OAuthTokenResponse:
    if not body.refresh_token:
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


def _handle_authorization_code_grant(body: OAuthTokenRequest) -> OAuthTokenResponse:
    if not body.code or not body.redirect_uri:
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
    request: Request, body: OAuthTokenRequest
) -> OAuthTokenResponse:
    authorization = request.headers.get("Authorization")
    client_id, client_secret = _parse_authorization_header(authorization)

    access_token, expires_in, scope = auth_service.client_credentials(
        client_id, client_secret, body.scope
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
):
    match body.grant_type:
        case GrantType.PASSWORD:
            token_response = _handle_password_grant(body)
        case GrantType.REFRESH_TOKEN:
            token_response = _handle_refresh_token_grant(body)
        case GrantType.AUTHORIZATION_CODE:
            token_response = _handle_authorization_code_grant(body)
        case GrantType.CLIENT_CREDENTIALS:
            token_response = _handle_client_credentials_grant(request, body)
        case _:
            raise OAuthException(ERROR_MESSAGE_UNSUPPORTED_GRANT_TYPE)

    return JSONResponse(
        content=token_response.model_dump(exclude_none=True),
        status_code=status.HTTP_200_OK,
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
    )


@router.post("/oauth/revoke", status_code=status.HTTP_200_OK)
def revoke(
    jwt_token: Annotated[JWTToken, Depends(jwt_bearer)],
):
    auth_service.logout(jwt_token)


@router.get("/oauth/authorize")
def authorize(
    jwt_token: Annotated[JWTToken, Depends(jwt_bearer)],
    response_type: str,
    client_id: str,
    redirect_uri: str,
    scope: str | None = None,
    state: str | None = None,
    code_challenge: str | None = None,
    code_challenge_method: str | None = None,
) -> Response:
    if response_type != "code":
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

    return Response(
        status_code=status.HTTP_302_FOUND,
        headers={"Location": f"{redirect_uri}?{urlencode(query_params)}"},
    )


@router.post("/register")
@require_scope(["users:write"])
def register(
    body: RegistrationRequest, jwt_token: Annotated[JWTToken, Depends(jwt_bearer)]
) -> Response:
    user_id = user_service.register(
        body.email, body.password, body.username, body.display_name
    )

    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"Location": f"/api/v1/users/{user_id}"},
    )
