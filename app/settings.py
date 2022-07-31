from pydantic import BaseSettings


class Settings(BaseSettings):
    app_name: str
    app_stage: str
    app_timezone: str
    jwt_secret: str
    jwt_token_lifetime: int = 3600
    cache_service_base_url: str
