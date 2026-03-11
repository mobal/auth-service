import os

from aws_lambda_powertools.utilities import parameters
from pydantic import computed_field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str
    default_timezone: str
    aws_access_key_id: str
    aws_secret_access_key: str
    jwt_token_lifetime: int = 3600
    debug: bool = False
    stage: str
    rate_limiting: bool = False
    rate_limit_requests: int = 100
    rate_limit_duration_in_seconds: int = 60
    refresh_token_lifetime: int = 2592000  # 30 days
    jwt_issuer: str = ""
    user_service_client_id: str = "auth-service"

    @computed_field
    @property
    def user_service_base_url(self) -> str:
        return parameters.get_parameter(
            os.environ.get("USER_SERVICE_BASE_URL_SSM_PARAM_NAME")
        )

    @computed_field
    @property
    def jwt_secret(self) -> str:
        return parameters.get_parameter(
            os.environ.get("JWT_SECRET_SSM_PARAM_NAME"), decrypt=True
        )
