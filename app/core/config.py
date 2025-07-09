from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pathlib import Path

# load .env from the project root
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings(BaseSettings):
    APP_NAME: str
    FRONTEND_URL: str

    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_KEY: str

    SECRET_KEY: str
    REFRESH_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    RESET_TOKEN_EXPIRE_MINUTES: int = 30
    VERIFICATION_TOKEN_EXPIRE_MINUTES: int = 60

    MAIL_USERNAME: str = "kula.gozano.swu@phinmaed.com"
    MAIL_FROM_NAME: str = "Coraline"
    MAIL_FROM: str = "kula.gozano.swu@phinmaed.com"
    MAIL_PASSWORD: str = "pwxo bkha pfok efol"
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_USE_TLS: bool = True
    MAIL_USE_SSL: bool = False

    class config:
        case_sensitive = True


settings = Settings()
