import base64
from enum import StrEnum, auto
from typing import Annotated

from aws_lambda_powertools import Logger
from fastapi import APIRouter, Depends, Request, Response, status

from app.exceptions import OAuthException
from app.jwt_bearer import JWTBearer
from app.models.jwt import JWTToken
from app.models.request.oauth_revoke import OAuthRevokeRequest
from app.models.request.oauth_token import OAuthTokenRequest
from app.models.request.register import RegistrationRequest
from app.models.response.token import OAuthTokenResponse
from app.security.authorization import require_scope
from app.services.auth_service import AuthService
from app.services.user_service import UserService

logger = Logger()

TOKEN_RESPONSE_HEADERS = {
    "Cache-Control": "no-store",
    "Pragma": "no-cache",
}

auth_service = AuthService()
jwt_bearer = JWTBearer()
router = APIRouter()
user_service = UserService()


class GrantType(StrEnum):
    PASSWORD = auto()
    REFRESH_TOKEN = auto()
    CLIENT_CREDENTIALS = auto()


def _set_token_response_headers(response: Response) -> None:
    response.headers.update(TOKEN_RESPONSE_HEADERS)


def _parse_basic_auth(authorization: str | None) -> tuple[str, str]:
    if not authorization or not authorization.startswith("Basic "):
        raise OAuthException(
            "invalid_client",
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Basic"},
        )
    try:
        decoded = base64.b64decode(authorization[6:]).decode()
    except Exception:
        raise OAuthException(
            "invalid_client",
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Basic"},
        )
    client_id, _, client_secret = decoded.partition(":")
    return client_id, client_secret


@router.post(
    "/oauth/token",
    status_code=status.HTTP_200_OK,
    response_model=OAuthTokenResponse,
    response_model_exclude_none=True,
)
def token(
    request: Request,
    response: Response,
    body: Annotated[OAuthTokenRequest, Depends(OAuthTokenRequest.as_form)],
):
    _set_token_response_headers(response)

    match body.grant_type:
        case GrantType.PASSWORD:
            if not body.username or not body.password:
                raise OAuthException("invalid_request")
            access_token, refresh_token, expires_in, scope = auth_service.login(
                body.username, body.password, body.scope
            )
            return OAuthTokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=expires_in,
                scope=scope,
            )
        case GrantType.REFRESH_TOKEN:
            if not body.refresh_token:
                raise OAuthException("invalid_request")
            current_jwt = jwt_bearer(request)
            access_token, refresh_token, expires_in, scope = auth_service.refresh(
                current_jwt, body.refresh_token
            )
            return OAuthTokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=expires_in,
                scope=scope,
            )
        case GrantType.CLIENT_CREDENTIALS:
            authorization = request.headers.get("Authorization")
            client_id, client_secret = _parse_basic_auth(authorization)
            access_token, expires_in, scope = auth_service.client_credentials(
                client_id, client_secret, body.scope
            )
            return OAuthTokenResponse(
                access_token=access_token,
                expires_in=expires_in,
                scope=scope,
            )
        case _:
            raise OAuthException("unsupported_grant_type")


@router.post("/oauth/revoke", status_code=status.HTTP_200_OK)
def revoke(
    request: Request,
    body: Annotated[OAuthRevokeRequest, Depends(OAuthRevokeRequest.as_form)],
):
    current_jwt = jwt_bearer(request)
    auth_service.logout(current_jwt)


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
