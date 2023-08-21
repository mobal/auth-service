from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str
    app_timezone: str
    aws_access_key_id: str
    aws_secret_access_key: str
    jwt_secret: str
    jwt_token_lifetime: int = 3600
    cache_service_base_url: str
    debug: bool = False
    stage: str
