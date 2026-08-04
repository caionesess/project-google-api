import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    GOOGLE_APPLICATION_CREDENTIALS: str = "credentials/google-service-account.json"
    PORT: int = 8000
    DEBUG: bool = False
    SQLITE_DB_PATH: str = "data/gdocs2html.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()