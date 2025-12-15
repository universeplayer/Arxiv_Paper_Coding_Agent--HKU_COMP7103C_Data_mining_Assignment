"""Application-wide configuration helpers."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Environment-driven configuration."""

    model_name: Literal["gpt-5-mini"] = "gpt-5-mini"
    candidate_count: int = Field(default=2, ge=1, le=4)
    max_output_tokens: int = Field(default=3500, ge=256, le=4096)

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    api_key_file: Path | None = Field(default=None, alias="API_KEY_FILE")

    http_proxy: str | None = Field(default=None, alias="HTTP_PROXY")
    https_proxy: str | None = Field(default=None, alias="HTTPS_PROXY")

    arxiv_cache_ttl: int = Field(default=3600, alias="ARXIV_CACHE_TTL")
    default_output_dir: Path = Field(
        default=Path("/tmp/research_agent"),
        alias="DEFAULT_OUTPUT_DIR",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def load_settings() -> Settings:
    """Expose a cached settings instance."""

    settings = Settings()
    settings.default_output_dir.mkdir(parents=True, exist_ok=True)
    if settings.api_key_file is None:
        repo_root = Path(__file__).resolve().parents[2]
        candidate = repo_root / "API_key-openai.md"
        if candidate.exists():
            settings.api_key_file = candidate
    return settings

