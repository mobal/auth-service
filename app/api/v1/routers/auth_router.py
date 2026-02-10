from aws_lambda_powertools import Logger
from fastapi import APIRouter, Depends, status

from app.jwt_bearer import JWTBearer
from app.models.request.login import LoginSchema
from app.models.request.refresh import RefreshSchema
from app.models.response.token import TokenResponse
from app.services.auth_service import AuthService

logger = Logger()

auth_service = AuthService()
jwt_bearer = JWTBearer()
router = APIRouter()


@router.post("/login", status_code=status.HTTP_200_OK)
def login(body: LoginSchema) -> TokenResponse:
    jwt_token, refresh_token, expires_in = auth_service.login(
        str(body.email), body.password
    )
    return TokenResponse(
        access_token=jwt_token, refresh_token=refresh_token, expires_in=expires_in
    )


@router.get(
    "/logout",
    dependencies=[Depends(jwt_bearer)],
    status_code=status.HTTP_204_NO_CONTENT,
)
def logout():
    auth_service.logout(jwt_bearer.decoded_token)


@router.post(
    "/refresh",
    dependencies=[Depends(jwt_bearer)],
    status_code=status.HTTP_200_OK,
)
def refresh(body: RefreshSchema) -> TokenResponse:
    jwt_token, refresh_token, expires_in = auth_service.refresh(
        jwt_bearer.decoded_token, body.refresh_token
    )
    return TokenResponse(
        access_token=jwt_token, refresh_token=refresh_token, expires_in=expires_in
    )
