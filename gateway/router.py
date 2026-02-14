"""
Model Router for Gonka.ai gateway.

Routes incoming requests to the correct vLLM backend based on the
model parameter in the request body. Reads model registry from models.yaml.
"""

import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from fastapi import HTTPException


@dataclass
class ModelBackend:
    name: str
    display_name: str
    provider: str
    model_id: str
    tier: str
    backend_url: str
    capabilities: list[str]
    context_length: int
    pricing: dict


class ModelRouter:
    """Routes requests to appropriate vLLM backends based on model name."""

    def __init__(self, config_path: str = "infrastructure/config/models.yaml"):
        self._backends: dict[str, ModelBackend] = {}
        self._config_path = config_path
        self.reload()

    def reload(self):
        """Reload model configuration from YAML."""
        path = Path(self._config_path)
        if not path.exists():
            return

        with open(path) as f:
            config = yaml.safe_load(f)

        self._backends.clear()
        for name, model_config in config.get("models", {}).items():
            self._backends[name] = ModelBackend(
                name=name,
                display_name=model_config.get("display_name", name),
                provider=model_config.get("provider", "unknown"),
                model_id=model_config.get("model_id", name),
                tier=model_config.get("tier", "standard"),
                backend_url=model_config.get("backend_url", "http://localhost:8000"),
                capabilities=model_config.get("capabilities", ["chat"]),
                context_length=model_config.get("context_length", 4096),
                pricing=model_config.get("pricing", {}),
            )

    def resolve(self, model_name: str) -> ModelBackend:
        """Resolve a model name to its backend configuration."""
        backend = self._backends.get(model_name)
        if not backend:
            available = list(self._backends.keys())
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "message": f"Model '{model_name}' not found. Available: {available}",
                        "type": "invalid_request_error",
                        "code": "model_not_found",
                    }
                },
            )
        return backend

    def list_models(self) -> list[dict]:
        """List available models in OpenAI /v1/models format."""
        return [
            {
                "id": name,
                "object": "model",
                "created": 0,
                "owned_by": backend.provider,
                "permission": [],
                "root": backend.model_id,
                "parent": None,
            }
            for name, backend in self._backends.items()
        ]

    def get_default_model(self) -> Optional[str]:
        """Get the default model name (first registered)."""
        if self._backends:
            return next(iter(self._backends))
        return None

    @property
    def model_count(self) -> int:
        return len(self._backends)
