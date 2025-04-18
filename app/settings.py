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
    refresh_token_lifetime: int = 1209600
    stage: str

    @computed_field
    @property
    def jwt_secret(self) -> str:
        return parameters.get_parameter(
            os.environ.get("JWT_SECRET_SSM_PARAM_NAME"), decrypt=True
        )
