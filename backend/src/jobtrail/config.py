from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    database_url: str = "postgresql+psycopg://jobtrail:jobtrail@db:5432/jobtrail"
    max_raw_text_chars: int = 50_000
    default_page_limit: int = 50
    max_page_limit: int = 200
    upcoming_days: int = 7
    stale_waiting_days: int = 7
    stale_source_days: int = 90


@lru_cache
def get_settings() -> Settings:
    return Settings()
