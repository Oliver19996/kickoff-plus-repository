from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    football_data_token: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    refresh_token: str = "change-me"
    app_base_url: str = "http://127.0.0.1:8000"
    database_url: str = "sqlite:///./data/kickoff.sqlite3"
    ingest_on_startup: bool = True
    ingest_on_request: bool = True
    start_scheduler: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
