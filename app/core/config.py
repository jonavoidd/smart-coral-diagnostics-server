from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional

# load .env from the project root
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings(BaseSettings):
    ENV: str
    APP_NAME: str
    FRONTEND_URL: str
    BACKEND_URL: str
    PROD_FRONTEND_URL: str
    PROD_BACKEND_URL: str

    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_KEY: str

    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str

    SECRET_KEY: str
    REFRESH_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    SESSION_SECRET: str

    RESET_TOKEN_EXPIRE_MINUTES: int = 30
    VERIFICATION_TOKEN_EXPIRE_HOURS: int = 60

    MAIL_USERNAME: str = "kula.gozano.swu@phinmaed.com"
    MAIL_FROM_NAME: str = "Coraline"
    MAIL_FROM: str = "kula.gozano.swu@phinmaed.com"
    MAIL_PASSWORD: str = "pwxo bkha pfok efol"
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_USE_TLS: bool = True
    MAIL_USE_SSL: bool = False

    BLEACHING_MODEL_NAME: str = "microsoft/resnet-50"
    BLEACHING_MODEL_CACHE_DIR: str = "./models_cache"
    BLEACHING_CONFIDENCE_THRESHOLD: float = 0.7
    MODEL_DEVICE: str = "cpu"

    CUSTOM_BLEACHING_MODEL_PATH: Optional[str] = None

    HF_MODEL_NAME: str
    HF_USERNAME: str
    HF_MODEL_FILENAME: str
    HF_ACCESS_TOKEN: str

    OPEN_ROUTER_API_KEY: str
    TOGETHER_AI_API_KEY: str

    REDIS_URL: str

    TRANSACTION_POOLER: str

    class config:
        case_sensitive = True


settings = Settings()
