from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pydantic import field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    app_name: str = "LoL Stats API"
    app_version: str = "0.1.0"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/lol_stats"
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_pool_size: int = 10

    # Riot API
    riot_api_key: str = ""
    riot_api_base_url: str = "https://americas.api.riotgames.com"
    riot_api_region_url: str = "https://na1.api.riotgames.com"
    riot_api_rate_limit_per_second: int = 20
    riot_api_rate_limit_per_minute: int = 100
    riot_api_timeout: int = 30

    # Cache TTL (seconds)
    cache_ttl_player: int = 3600  # 1 hour
    cache_ttl_match: int = 1800  # 30 minutes
    cache_ttl_stats: int = 900   # 15 minutes
    cache_ttl_analysis: int = 7200  # 2 hours
    cache_ttl_patch_notes: int = 1800  # 30 minutes

    # OP.GG scraper settings
    opgg_enabled: bool = True  # Feature flag - set to False to disable
    opgg_cache_ttl: int = 21600  # 6 hours
    opgg_timeout: int = 30
    opgg_rate_limit_per_second: int = 2
    opgg_max_retries: int = 2

    # AI Coach / OpenAI
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_api_mode: str = "responses"  # responses | chat
    coach_default_match_limit: int = 20
    coach_prompt_version: str = "coach-v1"

    # CORS
    cors_origins: list[str] = ["*"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, str):
            if value.strip() == "":
                return ["*"]
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
