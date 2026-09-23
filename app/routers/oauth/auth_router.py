import base64
from pathlib import Path
from typing import Annotated
from urllib.parse import urlencode

from aws_lambda_powertools import Logger, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from app import settings
from app.clients.google_oidc_client import GoogleOIDCClient
from app.dependencies import (
    get_auth_service,
    get_browser_session_repository,
    get_google_oidc_client,
    get_google_oidc_state_repository,
    get_jwt_bearer,
    get_optional_jwt_bearer,
    get_pending_authorization_request_repository,
)
from app.exceptions import (
    InvalidCredentialsException,
    OAuthException,
)
from app.models.authorization_decision import AuthorizationDecision
from app.models.grant_type import GrantType
from app.models.jwt import JWTToken
from app.models.login_page import LoginPage
from app.models.pending_authorization_request import PendingAuthorizationRequest
from app.models.request.oauth_token import (
    AuthorizationCodeGrantRequest,
    BaseGrantRequest,
    ClientCredentialsGrantRequest,
    PasswordGrantRequest,
    RefreshTokenGrantRequest,
)
from app.repositories.browser_session_repository import BrowserSessionRepository
from app.repositories.google_oidc_state_repository import GoogleOIDCStateRepository
from app.repositories.pending_authorization_request_repository import (
    PendingAuthorizationRequestRepository,
)
from app.services.auth_service import AuthService

logger = Logger()
metrics = Metrics(namespace="AuthService")

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[2] / "templates")

ERROR_MESSAGE_AUTHORIZATION_REQUEST_EXPIRED_OR_INVALID = (
    "Authorization request expired or invalid."
)
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
    form = {key: value for key, value in form_data.items() if isinstance(value, str)}
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
    client_name = client_secret = None
    if isinstance(body, ClientCredentialsGrantRequest):
        client_name, client_secret = _parse_authorization_header(
            request.headers.get("Authorization")
        )
    token_response = auth_service.issue_token(body, client_name, client_secret)

    if isinstance(body, PasswordGrantRequest):
        logger.warning(
            "Password grant used — this flow is deprecated per OAuth 2.1 (BCP). "
            "Migrate clients to authorization code grant with PKCE.",
            extra={"client_id": body.client_id},
        )
        metrics.add_metric(
            name="oauth_password_grant_requests_total",
            unit=MetricUnit.Count,
            value=1,
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


def _render_login_page(
    request: Request,
    page: LoginPage,
    status_code: int = status.HTTP_200_OK,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context=page.model_dump(),
        status_code=status_code,
    )


def _authorization_redirect(
    auth_service: AuthService,
    pending: PendingAuthorizationRequest,
    user_id: str,
) -> RedirectResponse:
    code = auth_service.authorize_pending_request(pending, user_id)
    query_params = _authorization_query_params(code, pending.state)
    return RedirectResponse(
        url=_append_query(pending.redirect_uri, query_params),
        status_code=status.HTTP_302_FOUND,
    )


def _authorization_query_params(code: str, state: str | None) -> dict[str, str]:
    query_params = {"code": code}
    if state is not None:
        query_params["state"] = state
    return query_params


def _append_query(uri: str, params: dict[str, str]) -> str:
    separator = "&" if "?" in uri else "?"
    return f"{uri}{separator}{urlencode(params)}"


def _authorization_response(decision: AuthorizationDecision) -> RedirectResponse:
    if decision.pending_request is not None:
        pending = decision.pending_request
        response = RedirectResponse(
            url=f"/login?{urlencode({'request_id': pending.id})}",
            status_code=status.HTTP_302_FOUND,
        )
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

    if decision.authorization_code is None:
        raise OAuthException("invalid_request")
    response = RedirectResponse(
        url=_append_query(
            decision.redirect_uri,
            _authorization_query_params(decision.authorization_code, decision.state),
        ),
        status_code=status.HTTP_302_FOUND,
    )
    return response


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
    response_type: str = Annotated[str, Query()],
    client_id: str = Annotated[str, Query()],
    redirect_uri: str = Annotated[str, Query()],
    scope: str | None = None,
    state: str | None = None,
    code_challenge: str | None = None,
    code_challenge_method: str | None = None,
) -> Response:
    session_id = request.cookies.get("auth_session")
    session = browser_sessions.get(session_id) if session_id else None
    decision = auth_service.process_authorization_request(
        response_type=response_type,
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scope,
        state=state,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        bearer_user_id=jwt_token.sub if jwt_token is not None else None,
        browser_session_user_id=session.user_id if session is not None else None,
        pending_requests=pending_requests,
    )
    return _authorization_response(decision)


@router.get("/login")
def login_page(
    request: Request,
    request_id: str,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    pending_requests: Annotated[
        PendingAuthorizationRequestRepository,
        Depends(get_pending_authorization_request_repository),
    ],
) -> HTMLResponse:
    page = auth_service.get_login_page(
        request_id,
        pending_requests,
    )
    if page is None:
        return HTMLResponse(
            ERROR_MESSAGE_AUTHORIZATION_REQUEST_EXPIRED_OR_INVALID, status_code=400
        )
    return _render_login_page(request, page)


@router.get("/login/google")
def google_login(
    request: Request,
    request_id: str,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    pending_requests: Annotated[
        PendingAuthorizationRequestRepository,
        Depends(get_pending_authorization_request_repository),
    ],
    google_states: Annotated[
        GoogleOIDCStateRepository, Depends(get_google_oidc_state_repository)
    ],
    google_client: Annotated[GoogleOIDCClient, Depends(get_google_oidc_client)],
) -> Response:
    authorization_url = auth_service.start_google_login(
        request_id,
        request.cookies.get("login_csrf"),
        pending_requests,
        google_states,
        google_client,
    )
    if authorization_url is None:
        return HTMLResponse(
            ERROR_MESSAGE_AUTHORIZATION_REQUEST_EXPIRED_OR_INVALID, status_code=400
        )
    logger.info("Google login started", extra={"pending_request_id": request_id})
    return RedirectResponse(
        url=authorization_url,
        status_code=status.HTTP_302_FOUND,
    )


@router.get("/login/google/callback")
def google_callback(
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    browser_sessions: Annotated[
        BrowserSessionRepository, Depends(get_browser_session_repository)
    ],
    pending_requests: Annotated[
        PendingAuthorizationRequestRepository,
        Depends(get_pending_authorization_request_repository),
    ],
    google_states: Annotated[
        GoogleOIDCStateRepository, Depends(get_google_oidc_state_repository)
    ],
    google_client: Annotated[GoogleOIDCClient, Depends(get_google_oidc_client)],
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> Response:
    result = auth_service.complete_google_login(
        code, state, error, pending_requests, google_states, google_client
    )
    if result.status == "invalid_request":
        return HTMLResponse(
            result.error_message
            or ERROR_MESSAGE_AUTHORIZATION_REQUEST_EXPIRED_OR_INVALID,
            status_code=400,
        )
    if result.pending is None:
        return HTMLResponse(
            ERROR_MESSAGE_AUTHORIZATION_REQUEST_EXPIRED_OR_INVALID, status_code=400
        )
    if result.status == "error":
        page = auth_service.get_login_page(
            result.pending.id,
            pending_requests,
            result.error_message,
        )
        if page is None:
            return HTMLResponse(
                ERROR_MESSAGE_AUTHORIZATION_REQUEST_EXPIRED_OR_INVALID,
                status_code=400,
            )
        return _render_login_page(request, page)
    if result.user_id is None:
        return HTMLResponse(
            ERROR_MESSAGE_AUTHORIZATION_REQUEST_EXPIRED_OR_INVALID, status_code=400
        )

    response = _authorization_redirect(auth_service, result.pending, result.user_id)
    response.set_cookie(
        "auth_session",
        auth_service.create_browser_session(result.user_id, browser_sessions),
        max_age=settings.browser_session_lifetime_seconds,
        httponly=True,
        secure=settings.stage == "prod",
        samesite="lax",
        path="/",
    )
    response.delete_cookie("login_csrf", path="/")
    return response


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
    try:
        result = auth_service.complete_browser_login(
            request_id,
            str(form.get("csrf_token", "")),
            request.cookies.get("login_csrf"),
            str(form.get("email", "")),
            str(form.get("password", "")),
            pending_requests,
        )
    except InvalidCredentialsException:
        pending = auth_service.get_pending_authorization_request(
            request_id, pending_requests
        )
        if pending is None:
            return HTMLResponse(
                ERROR_MESSAGE_AUTHORIZATION_REQUEST_EXPIRED_OR_INVALID,
                status_code=400,
            )
        page = auth_service.get_login_page(
            request_id,
            pending_requests,
            "Invalid email or password.",
        )
        if page is None:
            return HTMLResponse(
                ERROR_MESSAGE_AUTHORIZATION_REQUEST_EXPIRED_OR_INVALID,
                status_code=400,
            )
        return _render_login_page(request, page)
    if result is None:
        return HTMLResponse(
            ERROR_MESSAGE_AUTHORIZATION_REQUEST_EXPIRED_OR_INVALID, status_code=400
        )
    consumed, user = result
    response = _authorization_redirect(auth_service, consumed, user["id"])
    response.set_cookie(
        "auth_session",
        auth_service.create_browser_session(user["id"], browser_sessions),
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
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    browser_sessions: Annotated[
        BrowserSessionRepository, Depends(get_browser_session_repository)
    ],
) -> Response:
    auth_service.logout_browser_session(
        request.cookies.get("auth_session"), browser_sessions
    )
    response.delete_cookie("auth_session", path="/")
    return response
