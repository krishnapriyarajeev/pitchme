"""Server settings, loaded once from the environment and `.env`."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = Field(default="dev", alias="APP_ENV")
    log_level: str = "INFO"
    log_dir: str = "logs"

    # Comma separated in the env: "http://localhost:8081,http://192.168.1.5:8081".
    # "*" is allowed only in dev; it turns off credentials (see server.main).
    cors_origins: Annotated[list[str], NoDecode] = ["*"]

    # ---- Postgres ----
    postgres_user: str = "pitchme"
    postgres_password: SecretStr = SecretStr("")
    postgres_db: str = "pitchme"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: SecretStr | None = None

    # ---- Object storage ----
    minio_root_user: str = "pitchme"
    minio_root_password: SecretStr = SecretStr("")
    media_bucket: str = "pitchme"
    s3_endpoint: str = "http://localhost:9000"
    s3_public_endpoint: str = ""
    s3_access_key: str = ""
    s3_secret_key: SecretStr = SecretStr("")
    s3_region: str = "us-east-1"

    # ---- Auth ----
    jwt_secret: SecretStr = SecretStr("")
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24

    # ---- Redis (analysis job queue) ----
    # Empty: redis://localhost:REDIS_PORT/0, the Redis from docker-compose.
    redis_url: SecretStr = SecretStr("")
    redis_port: int = 6379
    # A job running longer than this is stopped and marked failed.
    analysis_timeout_minutes: int = 30

    # ---- Agent worker callbacks ----
    ai_callback_key: SecretStr = SecretStr("")
    server_public_base_url: str = "http://localhost:8000"

    # ---- LiveKit ----
    livekit_url: str = "ws://localhost:7880"
    livekit_public_url: str = ""
    livekit_api_key: str = "devkey"
    livekit_api_secret: SecretStr = SecretStr("")
    # Empty: egress uploads with the storage in its own config, which
    # docker-compose points at MinIO. host.docker.internal, the old default,
    # does not resolve on Linux.
    egress_s3_endpoint: str = ""
    # How long the app has to join with its token.
    livekit_token_ttl_minutes: int = 10

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [o.strip() for o in value.split(",") if o.strip()]
        return value

    @property
    def is_dev(self) -> bool:
        return self.env == "dev"

    @property
    def db_url(self) -> str:
        """DATABASE_URL when set, else built from the POSTGRES_* parts."""
        if self.database_url:
            return self.database_url.get_secret_value()
        password = self.postgres_password.get_secret_value()
        return (
            f"postgresql+psycopg://{self.postgres_user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def storage_access_key(self) -> str:
        return self.s3_access_key or self.minio_root_user

    @property
    def storage_secret_key(self) -> str:
        return self.s3_secret_key.get_secret_value() or self.minio_root_password.get_secret_value()

    @property
    def storage_public_endpoint(self) -> str:
        """Host the phone uses for presigned URLs. Falls back to the internal endpoint."""
        return self.s3_public_endpoint or self.s3_endpoint

    @property
    def redis_dsn(self) -> str:
        return self.redis_url.get_secret_value() or f"redis://localhost:{self.redis_port}/0"

    @property
    def livekit_client_url(self) -> str:
        """LiveKit URL handed to the app. Falls back to the internal URL."""
        return self.livekit_public_url or self.livekit_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
