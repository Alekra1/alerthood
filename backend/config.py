from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    supabase_url: str
    supabase_service_key: str
    supabase_jwt_secret: str
    scraper_interval_minutes: int = 15
    demo_city: str = "Chicago"
    cors_origins: list[str] = ["http://localhost:5173"]
    acled_api_key: str = ""
    acled_api_email: str = ""
    openweather_api_key: str = ""

    model_config = {"env_file": ".env"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
