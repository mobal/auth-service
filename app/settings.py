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
    cache_service_base_url: str
    debug: bool = False
    stage: str

    @computed_field
    @property
    def cache_service_api_key(self) -> str:
        return parameters.get_parameter(
            os.environ.get("CACHE_SERVICE_API_KEY_SSM_PARAM_NAME"), decrypt=True
        )

    @computed_field
    @property
    def jwt_secret(self) -> str:
        return parameters.get_parameter(
            os.environ.get("JWT_SECRET_SSM_PARAM_NAME"), decrypt=True
        )
