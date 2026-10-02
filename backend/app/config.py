from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str
    webapp_url: str = ""
    database_url: str
    redis_url: str = ""
    admin_ids: str = ""
    cors_origins: str = "*"
    log_level: str = "INFO"

    sherlock_daily_limit_free: int = 5
    sherlock_daily_limit_pro: int = 100
    sherlock_daily_limit_ultra: int = 500

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def admin_id_set(self) -> set[int]:
        return {
            int(x.strip())
            for x in self.admin_ids.split(",")
            if x.strip().isdigit()
        }

    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

    @property
    def async_database_url(self) -> str:
        # Blitz supplies a standard postgresql:// DATABASE_URL.
        # SQLAlchemy's asyncpg driver needs postgresql+asyncpg://.
        if self.database_url.startswith("postgresql+asyncpg://"):
            return self.database_url
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
