from functools import lru_cache
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./bantu.db"
    jwt_secret: str = "change-this-hackathon-secret"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60
    env: str = "development"
    fapshi_public_user: SecretStr | None = None
    fapshi_api_key: SecretStr | None = None
    fapshi_webhook_secret: SecretStr | None = None
    fapshi_base_url: str = "https://sandbox.fapshi.com"
    fapshi_redirect_url: str = "http://127.0.0.1:8000/payments/fapshi/callback"


@lru_cache
def get_settings() -> Settings:
    return Settings()
