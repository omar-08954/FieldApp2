from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_name: str = "FieldApp API"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://fieldapp:fieldapp@localhost:5432/fieldapp"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "development-secret-change-me-before-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 14
    frontend_origins: str = "http://localhost:3000"
    initial_admin_username: str = ""
    initial_admin_password: str = ""
    initial_admin_name: str = "مسؤول النظام"
    default_technician_password: str = ""
    ai_enabled: bool = False
    ai_base_url: str = "https://api.openai.com/v1"
    ai_api_key: str = ""
    ai_model: str = "gpt-4.1-mini"
    uploads_dir: str = "uploads"
    logs_dir: str = "logs"
    log_max_bytes: int = 10 * 1024 * 1024
    log_backup_count: int = 10
    max_upload_bytes: int = 5 * 1024 * 1024
    r2_endpoint_url: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket: str = ""

    @field_validator("database_url", mode="before")
    @classmethod
    def use_psycopg_driver(cls, value: str) -> str:
        """Accept standard PostgreSQL URLs as supplied by managed providers."""
        url = str(value)
        if url.startswith("postgresql://"):
            return "postgresql+psycopg://" + url.removeprefix("postgresql://")
        if url.startswith("postgres://"):
            return "postgresql+psycopg://" + url.removeprefix("postgres://")
        return url

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]

    @property
    def uses_r2_storage(self) -> bool:
        return all((self.r2_endpoint_url, self.r2_access_key_id, self.r2_secret_access_key, self.r2_bucket))


@lru_cache
def get_settings() -> Settings:
    return Settings()
