from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_service_key: str = ""
    pipedrive_api_token: str = "6ac95793e7cb8a18b3c0c4d11b3eba89b3754820"
    theirstack_api_key: str = ""
    brave_api_key: str = ""
    exa_api_key: str = ""
    apollo_api_key: str = ""
    # Optional: restrict to Prereads US pipeline only
    pipedrive_pipeline_name: str = "Prereads US"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
