from aws_lambda_powertools import Logger
from fastapi import APIRouter, status, Depends

from app.jwt_bearer import JWTBearer
from app.schemas import LoginSchema, RefreshSchema
from app.services import AuthService

logger = Logger()

auth_service = AuthService()
jwt_bearer = JWTBearer()
router = APIRouter()

@router.post("/api/v1/login", status_code=status.HTTP_200_OK)
def login(body: LoginSchema) -> dict[str, str]:
    jwt_token, refresh_token = auth_service.login(str(body.email), body.password)
    return {
        "token": jwt_token,
        "refreshToken": refresh_token,
    }


@router.get(
    "/api/v1/logout",
    dependencies=[Depends(jwt_bearer)],
    status_code=status.HTTP_204_NO_CONTENT,
)
def logout():
    auth_service.logout(jwt_bearer.decoded_token)


@router.post(
    "/api/v1/refresh",
    dependencies=[Depends(jwt_bearer)],
    status_code=status.HTTP_200_OK,
)
def refresh(body: RefreshSchema) -> dict[str, str]:
    jwt_token, refresh_token = auth_service.refresh(
        jwt_bearer.decoded_token, body.refresh_token
    )
    return {"token": jwt_token, "refreshToken": refresh_token}
