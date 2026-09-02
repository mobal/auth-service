from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from aws_lambda_powertools import Logger

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # not available on AWS Lambda

from app.settings import Settings

env_files = [".env", ".env.dev", ".env.local", ".env.prod"]


def load_env_files() -> None:
    root_dir = Path(__file__).parent.parent
    for env in env_files:
        f = root_dir / env
        if f.exists():
            if load_dotenv is not None:
                load_dotenv(dotenv_path=f, override=True)


load_env_files()

logger = Logger()
settings = Settings()

# Validate the configured IANA timezone at startup so a misconfigured
# DEFAULT_TIMEZONE fails fast with a clear message instead of a cryptic
# error the first time a timezone is actually needed.
try:
    ZoneInfo(settings.default_timezone)
except (ValueError, ZoneInfoNotFoundError) as e:
    raise ValueError(f"Invalid DEFAULT_TIMEZONE: {settings.default_timezone!r}") from e
