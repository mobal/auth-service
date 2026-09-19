import base64
import html
from typing import Annotated
from urllib.parse import urlencode

from aws_lambda_powertools import Logger, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import ValidationError

from app import settings
from app.dependencies import (
    get_auth_service,
    get_browser_session_repository,
    get_jwt_bearer,
    get_optional_jwt_bearer,
    get_pending_authorization_request_repository,
)
from app.exceptions import InvalidCredentialsException, OAuthException
from app.models.grant_type import GrantType
from app.models.jwt import JWTToken
from app.models.pending_authorization_request import PendingAuthorizationRequest
from app.models.request.oauth_token import (
    AuthorizationCodeGrantRequest,
    BaseGrantRequest,
    ClientCredentialsGrantRequest,
    PasswordGrantRequest,
    RefreshTokenGrantRequest,
)
from app.models.response.token import OAuthTokenResponse
from app.repositories.browser_session_repository import BrowserSessionRepository
from app.repositories.pending_authorization_request_repository import (
    PendingAuthorizationRequestRepository,
)
from app.services.auth_service import AuthService

logger = Logger()
metrics = Metrics(namespace="AuthService")

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
    form_data = await request.form()
    form = {
        key: value for key, value in form_data.items() if isinstance(value, str)
    }
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
        extra={
            "oauth_password_grant_requests_total": 1,
            "client_id": body.client_id,
        },
    )
    metrics.add_metric(
        name="oauth_password_grant_requests_total",
        unit=MetricUnit.Count,
        value=1,
    )

    access_token, refresh_token, expires_in, scope = auth_service.login(
        body.username, body.password, body.scope, body.resource
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
        body.code, body.redirect_uri, body.code_verifier, body.client_id
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
        client_name, client_secret, body.scope, resource=body.resource
    )

    return OAuthTokenResponse(
        access_token=access_token,
        expires_in=expires_in,
        scope=scope,
    )


@router.post(
    "/oauth/token",
    status_code=status.HTTP_200_OK,
    description=(
        "Supports authorization_code, refresh_token, and client_credentials. "
        "The password grant is deprecated and retained for legacy compatibility."
    ),
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
            auth_service.validate_grant_type(body.client_id, "password")
            token_response = _handle_password_grant(body, auth_service)
        case RefreshTokenGrantRequest():
            token_response = _handle_refresh_token_grant(body, auth_service)
        case AuthorizationCodeGrantRequest():
            auth_service.validate_grant_type(body.client_id, "authorization_code")
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


def _login_page(
    request_id: str,
    csrf_token: str,
    error: str | None = None,
) -> HTMLResponse:
    escaped_request_id = html.escape(request_id, quote=True)
    message = html.escape(error or "", quote=False)
    content = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sign in</title><style>
body{{font-family:system-ui,sans-serif;background:#f4f6f8;display:grid;place-items:center;min-height:100vh;margin:0}}
main{{background:#fff;padding:2rem;border-radius:.75rem;box-shadow:0 .5rem 2rem #0002;width:min(22rem,calc(100% - 3rem))}}
label{{display:block;margin:.9rem 0 .3rem}}input{{box-sizing:border-box;width:100%;padding:.7rem;border:1px solid #bbc3cc;border-radius:.35rem}}
button{{width:100%;margin-top:1.2rem;padding:.75rem;border:0;border-radius:.35rem;background:#175cd3;color:#fff;font-weight:600}}
.error{{color:#b42318;min-height:1.4rem}}h1{{margin-top:0}}
</style></head><body><main><h1>Sign in</h1><div class="error" role="alert">{message}</div>
<form method="post" action="/login"><input type="hidden" name="request_id" value="{escaped_request_id}">
<input type="hidden" name="csrf_token" value="{html.escape(csrf_token, quote=True)}">
<label for="email">Email</label><input id="email" name="email" type="email" autocomplete="username" required>
<label for="password">Password</label><input id="password" name="password" type="password" autocomplete="current-password" required>
<button type="submit">Sign in</button></form></main></body></html>"""
    return HTMLResponse(content)


def _authorization_redirect(
    auth_service: AuthService,
    pending: PendingAuthorizationRequest,
    user_id: str,
) -> RedirectResponse:
    code = auth_service.authorize(
        user_id=user_id,
        client_id=pending.client_id,
        redirect_uri=pending.redirect_uri,
        requested_scope=pending.scope,
        code_challenge=pending.code_challenge,
        code_challenge_method=pending.code_challenge_method,
    )
    query_params = {"code": code}
    if pending.state:
        query_params["state"] = pending.state
    return RedirectResponse(
        url=_append_query(pending.redirect_uri, query_params),
        status_code=status.HTTP_302_FOUND,
    )


def _append_query(uri: str, params: dict[str, str]) -> str:
    separator = "&" if "?" in uri else "?"
    return f"{uri}{separator}{urlencode(params)}"


@router.get("/oauth/authorize")
def authorize(
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    browser_sessions: Annotated[
        BrowserSessionRepository, Depends(get_browser_session_repository)
    ],
    pending_requests: Annotated[
        PendingAuthorizationRequestRepository,
        Depends(get_pending_authorization_request_repository),
    ],
    jwt_token: Annotated[JWTToken | None, Depends(get_optional_jwt_bearer)],
    response_type: str = Query(...),
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    scope: str | None = None,
    state: str | None = None,
    code_challenge: str | None = None,
    code_challenge_method: str | None = None,
) -> Response:
    if jwt_token is None:
        auth_service.validate_authorization_request(
            response_type,
            client_id,
            redirect_uri,
            code_challenge,
            code_challenge_method,
        )
        assert code_challenge is not None
        assert code_challenge_method is not None
        session_id = request.cookies.get("auth_session")
        session = browser_sessions.get(session_id) if session_id else None
        if session is None:
            request_id = pending_requests.create(
                client_id=client_id,
                redirect_uri=redirect_uri,
                response_type=response_type,
                scope=scope,
                state=state,
                code_challenge=code_challenge,
                code_challenge_method=code_challenge_method,
                lifetime_seconds=settings.pending_authorization_request_lifetime_seconds,
            )
            response = RedirectResponse(
                url=f"/login?request_id={urlencode({'': request_id})[1:]}",
                status_code=status.HTTP_302_FOUND,
            )
            pending = pending_requests.get(request_id)
            if pending is None:
                raise OAuthException("invalid_request")
            response.set_cookie(
                "login_csrf",
                pending.csrf_token,
                max_age=settings.pending_authorization_request_lifetime_seconds,
                httponly=True,
                secure=settings.stage == "prod",
                samesite="lax",
                path="/",
            )
            return response
        code = auth_service.authorize(
            user_id=session.user_id,
            client_id=client_id,
            redirect_uri=redirect_uri,
            requested_scope=scope,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
        )
        query_params = {"code": code}
        if state:
            query_params["state"] = state
        return RedirectResponse(
            url=_append_query(redirect_uri, query_params),
            status_code=status.HTTP_302_FOUND,
        )

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
        headers={"Location": _append_query(redirect_uri, query_params)},
    )


@router.get("/login")
def login_page(
    request_id: str,
    pending_requests: Annotated[
        PendingAuthorizationRequestRepository,
        Depends(get_pending_authorization_request_repository),
    ],
) -> HTMLResponse:
    pending = pending_requests.get(request_id)
    if pending is None:
        return HTMLResponse(
            "Authorization request expired or invalid.", status_code=400
        )
    return _login_page(request_id, pending.csrf_token)


@router.post("/login")
async def login(
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    browser_sessions: Annotated[
        BrowserSessionRepository, Depends(get_browser_session_repository)
    ],
    pending_requests: Annotated[
        PendingAuthorizationRequestRepository,
        Depends(get_pending_authorization_request_repository),
    ],
) -> Response:
    form = dict(await request.form())
    request_id = str(form.get("request_id", ""))
    pending = pending_requests.get(request_id)
    if (
        pending is None
        or form.get("csrf_token") != pending.csrf_token
        or request.cookies.get("login_csrf") != pending.csrf_token
    ):
        return HTMLResponse(
            "Authorization request expired or invalid.", status_code=400
        )

    try:
        user = auth_service.authenticate_user(
            str(form.get("email", "")), str(form.get("password", ""))
        )
    except InvalidCredentialsException:
        return _login_page(request_id, pending.csrf_token, "Invalid email or password.")

    consumed = pending_requests.consume(request_id)
    if consumed is None:
        return HTMLResponse(
            "Authorization request expired or invalid.", status_code=400
        )
    response = _authorization_redirect(auth_service, consumed, user["id"])
    response.set_cookie(
        "auth_session",
        browser_sessions.create(user["id"], settings.browser_session_lifetime_seconds),
        max_age=settings.browser_session_lifetime_seconds,
        httponly=True,
        secure=settings.stage == "prod",
        samesite="lax",
        path="/",
    )
    response.delete_cookie("login_csrf", path="/")
    return response


@router.post("/logout")
def browser_logout(
    request: Request,
    response: Response,
    browser_sessions: Annotated[
        BrowserSessionRepository, Depends(get_browser_session_repository)
    ],
) -> Response:
    session_id = request.cookies.get("auth_session")
    if session_id:
        browser_sessions.delete(session_id)
    response.delete_cookie("auth_session", path="/")
    return response
