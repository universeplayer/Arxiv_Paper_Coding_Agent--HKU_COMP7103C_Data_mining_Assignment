"""Configuration management for the agent system using Pydantic settings."""

import os
from pathlib import Path
from typing import Literal, Optional, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """System configuration with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM API Keys
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    deepseek_api_key: Optional[str] = Field(default=None, description="DeepSeek API key")
    qwen_api_key: Optional[str] = Field(default=None, description="Qwen API key")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")

    # API Key Files for Parallel Execution
    openai_api_key_file: Optional[str] = Field(
        default="API_keys_openai.txt",
        description="File containing multiple OpenAI API keys"
    )
    qwen_api_key_file: Optional[str] = Field(
        default="API_keys_qwen.txt",
        description="File containing multiple Qwen API keys"
    )

    # API Base URLs
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI API base URL"
    )
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com/v1",
        description="DeepSeek API base URL"
    )
    qwen_base_url: str = Field(
        default="https://dashscope.aliyuncs.com/api/v1",
        description="Qwen API base URL"
    )

    # Model Configurations
    default_model: str = Field(
        default="deepseek-chat",
        description="Default model to use"
    )
    planner_model: str = Field(
        default="deepseek-chat",
        description="Model for planning agent"
    )
    coder_model: str = Field(
        default="deepseek-chat",
        description="Model for coding agent"
    )
    reviewer_model: str = Field(
        default="deepseek-chat",
        description="Model for review agent"
    )

    @field_validator("default_model", "planner_model", "coder_model", "reviewer_model", mode="before")
    @classmethod
    def normalize_model_name(cls, value: Optional[str]):
        """Strip whitespace so models from .env stay valid."""
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("planner_model", "coder_model", "reviewer_model", mode="after")
    @classmethod
    def fallback_to_default(cls, value: str, info):
        """Use default_model when specific role model is empty."""
        if value and value.strip():
            return value
        default_model = info.data.get("default_model") if hasattr(info, "data") else None
        return default_model or ""

    # System Settings
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    timeout_seconds: int = Field(default=60, ge=10, le=600, description="Request timeout")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level"
    )
    enable_parallel_execution: bool = Field(
        default=True,
        description="Enable parallel task execution"
    )

    enable_arxiv_shortcuts: bool = Field(
        default=True,
        description="Auto-detect arXiv tasks via keywords"
    )

    # Parallel API Settings
    max_parallel_calls: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum parallel API calls for speedup"
    )
    candidate_count: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of candidate responses for ensemble"
    )

    # Rate Limiting
    max_requests_per_minute: int = Field(
        default=50,
        ge=1,
        le=1000,
        description="Max API requests per minute"
    )
    max_tokens_per_request: int = Field(
        default=4000,
        ge=100,
        le=128000,
        description="Max tokens per request"
    )

    # arXiv Settings
    arxiv_max_results: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Max papers to fetch from arXiv"
    )
    arxiv_categories: str = Field(
        default="cs.AI,cs.CL,cs.LG,cs.CV",
        description="Comma-separated arXiv categories"
    )

    # Output Directories
    output_dir: Path = Field(default=Path("./outputs"), description="Output directory")
    logs_dir: Path = Field(default=Path("./logs"), description="Logs directory")
    cache_dir: Path = Field(default=Path("./cache"), description="Cache directory")

    @field_validator("output_dir", "logs_dir", "cache_dir", mode="after")
    @classmethod
    def create_directories(cls, path: Path) -> Path:
        """Ensure directories exist."""
        path.mkdir(parents=True, exist_ok=True)
        return path

    @field_validator("arxiv_categories", mode="after")
    @classmethod
    def parse_categories(cls, categories: str) -> str:
        """Validate and normalize categories."""
        return ",".join(cat.strip() for cat in categories.split(",") if cat.strip())

    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for a specific provider."""
        key_map = {
            "openai": self.openai_api_key,
            "deepseek": self.deepseek_api_key,
            "qwen": self.qwen_api_key,
        }
        return key_map.get(provider.lower())

    def get_base_url(self, provider: str) -> str:
        """Get base URL for a specific provider."""
        url_map = {
            "openai": self.openai_base_url,
            "deepseek": self.deepseek_base_url,
            "qwen": self.qwen_base_url,
        }
        return url_map.get(provider.lower(), self.openai_base_url)

    @property
    def arxiv_categories_list(self) -> List[str]:
        """Get arXiv categories as a list."""
        return [cat.strip() for cat in self.arxiv_categories.split(",")]


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment."""
    global _settings
    _settings = Settings()
    return _settings
