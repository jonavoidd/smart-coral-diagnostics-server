from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from pathlib import Path

# load .env from the project root
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings(BaseSettings):
    SECRET_KEY: str
    REFRESH_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str

    class config:
        case_sensitive = True


settings = Settings()
