from typing import Annotated

from aws_lambda_powertools import Logger
from fastapi import APIRouter, Depends, Response, status

from app.jwt_bearer import JWTBearer
from app.models.jwt import JWTToken
from app.models.request.login import LoginRequest
from app.models.request.refresh import RefreshRequest
from app.models.request.register import RegistrationRequest
from app.models.response.token import TokenResponse
from app.security.authorization import pre_authorize
from app.services.auth_service import AuthService
from app.services.user_service import UserService

logger = Logger()

auth_service = AuthService()
jwt_bearer = JWTBearer()
router = APIRouter()
user_service = UserService()


@router.post("/login", status_code=status.HTTP_200_OK)
def login(body: LoginRequest) -> TokenResponse:
    jwt_token, refresh_token, expires_in = auth_service.login(
        str(body.email), body.password
    )

    return TokenResponse(
        access_token=jwt_token, refresh_token=refresh_token, expires_in=expires_in
    )


@router.get(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
def logout(jwt_token: Annotated[JWTToken, Depends(jwt_bearer)]):
    auth_service.logout(jwt_token)


@router.post(
    "/refresh",
    status_code=status.HTTP_200_OK,
)
def refresh(
    body: RefreshRequest, jwt_token: Annotated[JWTToken, Depends(jwt_bearer)]
) -> TokenResponse:
    jwt_token, refresh_token, expires_in = auth_service.refresh(
        jwt_token, body.refresh_token
    )

    return TokenResponse(
        access_token=jwt_token, refresh_token=refresh_token, expires_in=expires_in
    )


@router.post("/register")
@pre_authorize(["root"])
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
