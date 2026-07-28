"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg2://rwa:rwa_secret@localhost:5432/rwa_ledger"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    platform_fee_percent: str = "2.5"  # percent of rental income retained by platform
    api_base_url: str = "http://127.0.0.1:8000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
