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
    initial_admin_name: str = "أحمد شاهين"
    default_technician_password: str = ""
    ai_enabled: bool = False
    ai_base_url: str = "https://api.openai.com/v1"
    ai_api_key: str = ""
    ai_model: str = "gpt-4.1-mini"
    uploads_dir: str = "uploads"
    logs_dir: str = "logs"
    log_max_bytes: int = 10 * 1024 * 1024
    log_backup_count: int = 10
    max_upload_bytes: int = 25 * 1024 * 1024
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_reports_bucket: str = "fieldapp-reports"
    whatsapp_worker_secret: str = ""

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
    def uses_supabase_storage(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key and self.supabase_reports_bucket)


@lru_cache
def get_settings() -> Settings:
    return Settings()
