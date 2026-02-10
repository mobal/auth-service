from pathlib import Path

from dotenv import load_dotenv

from app.settings import Settings

PROJECT_DIR = Path(__file__).parent.parent

env_files = [".env", ".env.dev", ".env.local", ".env.prod"]

for env in env_files:
    f = PROJECT_DIR / env
    if f.exists():
        load_dotenv(dotenv_path=f, override=True)

settings = Settings()
