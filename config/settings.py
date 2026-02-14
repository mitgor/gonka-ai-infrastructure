"""
Gonka.ai Settings — centralized configuration via environment variables.

All settings have sensible defaults for local development.
Override with environment variables for production.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class VLLMBackend:
    """Configuration for a single vLLM model backend."""
    name: str
    url: str
    model_id: str
    tier: str = "standard"  # "premium", "standard", "budget"
    max_concurrent: int = 100


@dataclass
class Settings:
    """Application settings loaded from environment."""

    # Gateway
    gateway_host: str = field(default_factory=lambda: os.getenv("GONKA_GATEWAY_HOST", "0.0.0.0"))
    gateway_port: int = field(default_factory=lambda: int(os.getenv("GONKA_GATEWAY_PORT", "9000")))

    # vLLM backends
    vllm_base_url: str = field(default_factory=lambda: os.getenv("GONKA_VLLM_URL", "http://localhost:8000"))

    # Auth
    api_keys_file: str = field(default_factory=lambda: os.getenv("GONKA_API_KEYS_FILE", ""))
    admin_api_key: str = field(default_factory=lambda: os.getenv("GONKA_ADMIN_API_KEY", ""))

    # Rate limiting
    default_rpm: int = field(default_factory=lambda: int(os.getenv("GONKA_DEFAULT_RPM", "60")))
    default_tpm: int = field(default_factory=lambda: int(os.getenv("GONKA_DEFAULT_TPM", "100000")))

    # Sessions
    session_ttl_seconds: int = field(default_factory=lambda: int(os.getenv("GONKA_SESSION_TTL", "3600")))
    session_max_history: int = field(default_factory=lambda: int(os.getenv("GONKA_SESSION_MAX_HISTORY", "100")))

    # Memory
    memory_backend: str = field(default_factory=lambda: os.getenv("GONKA_MEMORY_BACKEND", "sqlite"))
    memory_db_path: str = field(default_factory=lambda: os.getenv("GONKA_MEMORY_DB", "data/memory.db"))

    # Data directory
    data_dir: str = field(default_factory=lambda: os.getenv("GONKA_DATA_DIR", "data"))

    def __post_init__(self):
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)


# Singleton
_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
