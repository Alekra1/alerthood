from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    supabase_url: str
    supabase_service_key: str
    supabase_jwt_secret: str
    scraper_interval_minutes: int = 15
    cors_origins: list[str] = [
        "http://localhost:5173",
        "https://alerthood.pages.dev",
    ]
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://openrouter.ai/api/v1"
    deepseek_model: str = "deepseek/deepseek-chat"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
