import os

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities import parameters
from pydantic import computed_field
from pydantic_settings import BaseSettings

logger = Logger()


class Settings(BaseSettings):
    app_name: str
    allowed_origins: list[str] = []
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
    service_token_lifetime_seconds: int = 30
    stage: str

    @computed_field
    def client_secret(self) -> str:
        logger.debug("Resolving client_secret from parameter store")
        param_name = os.environ.get("CLIENT_SECRET_SSM_PARAM_NAME")
        if param_name is None:
            raise ValueError("CLIENT_SECRET_SSM_PARAM_NAME is not set")
        return parameters.get_parameter(param_name, decrypt=True)

    @computed_field
    def jwt_secret(self) -> str:
        logger.debug("Resolving jwt_secret from parameter store")
        param_name = os.environ.get("JWT_SECRET_SSM_PARAM_NAME")
        if param_name is None:
            raise ValueError("JWT_SECRET_SSM_PARAM_NAME is not set")
        return parameters.get_parameter(param_name, decrypt=True)

    @computed_field
    def user_service_base_url(self) -> str:
        logger.debug("Resolving user_service_base_url from parameter store")
        param_name = os.environ.get("USER_SERVICE_BASE_URL_SSM_PARAM_NAME")
        if param_name is None:
            raise ValueError("USER_SERVICE_BASE_URL_SSM_PARAM_NAME is not set")
        return parameters.get_parameter(param_name)
