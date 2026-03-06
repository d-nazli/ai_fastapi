"""
Application settings — Pydantic Settings ile .env okuma
LM Studio + Webhook + CORS konfigürasyonu
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv


def init_settings():
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        validate_default=True,
    )

    # ── APP ────────────────────────────────────────────────
    app_name: str = Field(default="IntelliumAI Backend", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=True, alias="DEBUG")
    log_level: str = Field(default="info", alias="LOG_LEVEL")

    database_url: str = Field(default="postgresql+asyncpg://postgres:123456@localhost:5432/intelliumai", alias="DATABASE_URL")

    # ── LM STUDIO ─────────────────────────────────────────
    lm_studio_host: str = Field(default="localhost", alias="LM_STUDIO_HOST")
    lm_studio_port: int = Field(default=1234, alias="LM_STUDIO_PORT")
    ai_temperature: float = Field(default=0.3, alias="AI_TEMPERATURE")
    ai_timeout: int = Field(default=300, alias="AI_TIMEOUT")
    ai_model: str = Field(default="loaded-model", alias="AI_MODEL")

    @property
    def lm_studio_url(self) -> str:
        return f"http://{self.lm_studio_host}:{self.lm_studio_port}"

    @property
    def lm_studio_completions_url(self) -> str:
        return f"{self.lm_studio_url}/v1/chat/completions"

    # ── WEBHOOK ────────────────────────────────────────────
    webhook_url: str = Field(
        default="http://127.0.0.1:5000/api/mulakat_analizi/webhook",
        alias="WEBHOOK_URL",
    )
    webhook_api_key: str = Field(
        default="jo3AFL-iZclaXRwlUtUl07f0bhYTvWI1P9jD193mYAE",
        alias="WEBHOOK_API_KEY",
    )

    # ── CORS ───────────────────────────────────────────────
    cors_origins_raw: str = Field(default="*", alias="CORS_ORIGINS")

    @property
    def cors_origins(self) -> List[str]:
        v = self.cors_origins_raw.strip()
        if not v or v == "*":
            return ["*"]
        if v.startswith("["):
            import json
            try:
                return json.loads(v)
            except Exception:
                return ["*"]
        return [i.strip() for i in v.split(",") if i.strip()]

    # ── SERVER ─────────────────────────────────────────────
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    # ── TRANSCRIPT PATH ───────────────────────────────────
    transcript_base_dir: str = Field(default="", alias="TRANSCRIPT_BASE_DIR")

    # ── VALIDATORS ─────────────────────────────────────────
    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, v):
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return bool(v)

    @property
    def is_production(self) -> bool:
        return not self.debug

    @property
    def base_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent

    @property
    def project_root(self) -> Path:
        return self.base_dir.parent


settings = Settings()
