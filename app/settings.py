import os

from aws_lambda_powertools.utilities import parameters
from pydantic import computed_field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str
    default_timezone: str
    aws_access_key_id: str
    aws_secret_access_key: str
    debug: bool = False
    jwt_issuer: str = ""
    jwt_token_lifetime: int = 3600
    rate_limiting: bool = False
    rate_limit_requests: int = 100
    rate_limit_duration_in_seconds: int = 60
    refresh_token_lifetime: int = 2592000  # 30 days
    service_token_lifetime: int = 30
    stage: str

    @computed_field
    @property
    def client_secret(self) -> str:
        return parameters.get_parameter(
            os.environ.get("CLIENT_SECRET_SSM_PARAM_NAME"), decrypt=True
        )

    @computed_field
    @property
    def jwt_secret(self) -> str:
        return parameters.get_parameter(
            os.environ.get("JWT_SECRET_SSM_PARAM_NAME"), decrypt=True
        )

    @computed_field
    @property
    def user_service_base_url(self) -> str:
        return parameters.get_parameter(
            os.environ.get("USER_SERVICE_BASE_URL_SSM_PARAM_NAME")
        )
