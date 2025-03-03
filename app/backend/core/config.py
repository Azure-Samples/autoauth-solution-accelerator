from typing import Any

from pydantic import MongoDsn, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .constants import Environment


class CustomBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class Config(CustomBaseSettings):
    #
    DATABASE_URL: MongoDsn
    DATABASE_ASYNC_URL: MongoDsn
    AZURE_COSMOS_DB_DATABASE_NAME: str = ""

    ENVIRONMENT: Environment = Environment.LOCAL

    SENTRY_DSN: str | None = None

    CORS_ORIGINS: list[str] = ["*"]
    CORS_ORIGINS_REGEX: str | None = None
    CORS_HEADERS: list[str] = ["*"]

    APP_VERSION: str = "0.1"

    SECRET_KEY: str

    @model_validator(mode="after")
    def validate_sentry_non_local(self) -> "Config":
        if self.ENVIRONMENT.is_deployed and not self.SENTRY_DSN:
            raise ValueError("Sentry is not set")
        #
        return self


settings = Config()
#
# print("settings.DATABASE_URL:", settings.DATABASE_URL)
# print("settings.DATABASE_ASYNC_URL:", settings.DATABASE_ASYNC_URL)

app_configs: dict[str, Any] = {"title": "Prior Auth API App"}

if settings.ENVIRONMENT.is_deployed:
    app_configs["root_path"] = f"/v{settings.APP_VERSION}"

if not settings.ENVIRONMENT.is_debug:
    app_configs["openapi_url"] = None  # hide docs
