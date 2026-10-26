"""Read project-local configuration without displaying credentials."""

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
        env_prefix="MEMORYPILOT_",
    )

    provider: Literal["deepseek", "mock"] = Field(
        "deepseek", validation_alias="MEMORYPILOT_PROVIDER"
    )
    api_key: SecretStr = Field(SecretStr(""), validation_alias="DEEPSEEK_API_KEY")
    base_url: str = Field("https://api.deepseek.com", validation_alias="DEEPSEEK_BASE_URL")
    model: str = Field("deepseek-v4-pro", validation_alias="DEEPSEEK_MODEL")
    thinking: bool = Field(False, validation_alias="DEEPSEEK_THINKING")
    timeout: float = Field(60, gt=0, le=180, validation_alias="DEEPSEEK_TIMEOUT_SECONDS")
    max_output_tokens: int = Field(
        2048, ge=256, le=16384, validation_alias="MEMORYPILOT_MAX_OUTPUT_TOKENS"
    )
    max_model_calls: int = Field(8, ge=1, le=30, validation_alias="MEMORYPILOT_MAX_MODEL_CALLS")
    max_tool_calls: int = Field(6, ge=1, le=30, validation_alias="MEMORYPILOT_MAX_TOOL_CALLS")
    task_timeout: float = Field(
        180, gt=0, le=900, validation_alias="MEMORYPILOT_TASK_TIMEOUT_SECONDS"
    )
    context_budget: int = Field(
        8192, ge=1024, le=131072, validation_alias="MEMORYPILOT_CONTEXT_BUDGET"
    )
    data_dir: Path = Field(Path(".data"), validation_alias="MEMORYPILOT_DATA_DIR")

    @property
    def resolved_data_dir(self) -> Path:
        return self.data_dir if self.data_dir.is_absolute() else PROJECT_ROOT / self.data_dir


class ConfigurationError(ValueError):
    """A missing setting that the user can resolve locally."""
