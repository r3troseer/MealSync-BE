# import secrets
# from pydantic import field_validator
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    # Application
    PROJECT_NAME: str = "MealSync"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    # Security
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    # Database
    # Default to a local sqlite file for development; override via .env in production.
    DATABASE_URL: str = "sqlite:///./meal_sync.db"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    # AI Configuration
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash-lite"  # Default model for ingredients and recipes
    GEMINI_MEAL_PLAN_MODEL: str = "gemini-2.0-flash"  # More powerful model for meal planning
    GEMINI_TEMPERATURE: float = 0.7
    GEMINI_MAX_TOKENS: int = 2048
    GEMINI_API_TIMEOUT: int = 30

    # @field_validator("SECRET_KEY", mode="before")
    # @classmethod
    # def ensure_secret_key(cls, v, info):
    #     if not v:
    #         if info.data.get("DEBUG", False):
    #             print("[WARN] No SECRET_KEY found. Generating a temporary key for DEBUG mode.")
    #             return secrets.token_urlsafe(32)
    #         raise ValueError("SECRET_KEY is required in production!")
    #     return v

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE), case_sensitive=True, extra="ignore"
    )


settings = Settings()
