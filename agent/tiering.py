"""
Model Tiering for Gonka.ai agent inference.

Auto-routes requests to cheap or strong models based on configurable rules.
Agents can specify tiering preferences, or the system auto-detects based
on message content patterns.

Tiers:
- classification: Cheap, fast model for intent detection, tagging, classification
- reasoning: Strong model for multi-step planning, analysis, complex reasoning
- default: Balanced model for general chat
"""

import re
from dataclasses import dataclass, field
from typing import Optional

import yaml
from pathlib import Path


@dataclass
class TieringRule:
    pattern: str
    route_to: str  # "classification_model", "reasoning_model", "default_model"
    compiled: re.Pattern = field(init=False, repr=False)

    def __post_init__(self):
        self.compiled = re.compile(self.pattern, re.IGNORECASE)


@dataclass
class TieringConfig:
    classification_model: str = ""
    reasoning_model: str = ""
    default_model: str = ""
    rules: list[TieringRule] = field(default_factory=list)


class ModelTiering:
    """Auto-routes requests to appropriate model tier based on content analysis."""

    def __init__(self, config_path: str = "infrastructure/config/models.yaml"):
        self._config = TieringConfig()
        self._config_path = config_path
        self.reload()

    def reload(self):
        """Load tiering configuration from models.yaml."""
        path = Path(self._config_path)
        if not path.exists():
            return

        with open(path) as f:
            data = yaml.safe_load(f)

        tiering = data.get("tiering", {})
        self._config = TieringConfig(
            classification_model=tiering.get("classification_model", ""),
            reasoning_model=tiering.get("reasoning_model", ""),
            default_model=tiering.get("default_model", ""),
            rules=[
                TieringRule(
                    pattern=r.get("pattern", ""),
                    route_to=r.get("route_to", "default_model"),
                )
                for r in tiering.get("rules", [])
            ],
        )

    def resolve_model(self, messages: list[dict],
                      requested_model: Optional[str] = None,
                      tier_hint: Optional[str] = None) -> str:
        """
        Determine which model to use based on:
        1. Explicit tier hint from header (X-Gonka-Tier: reasoning|classification|default)
        2. Rule matching on message content
        3. Default model
        """
        # Explicit tier hint takes priority
        if tier_hint:
            model = self._resolve_tier(tier_hint)
            if model:
                return model

        # If explicit model requested, respect it
        if requested_model:
            return requested_model

        # Rule-based routing on last user message
        last_user_msg = self._get_last_user_message(messages)
        if last_user_msg:
            for rule in self._config.rules:
                if rule.compiled.search(last_user_msg):
                    model = self._resolve_tier(rule.route_to)
                    if model:
                        return model

        # Default
        return self._config.default_model or ""

    def _resolve_tier(self, tier: str) -> str:
        """Map tier name to actual model name."""
        mapping = {
            "classification_model": self._config.classification_model,
            "classification": self._config.classification_model,
            "reasoning_model": self._config.reasoning_model,
            "reasoning": self._config.reasoning_model,
            "default_model": self._config.default_model,
            "default": self._config.default_model,
        }
        return mapping.get(tier, "")

    def _get_last_user_message(self, messages: list[dict]) -> str:
        """Extract the last user message content."""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    return content
                elif isinstance(content, list):
                    # Multimodal content
                    return " ".join(
                        part.get("text", "")
                        for part in content
                        if part.get("type") == "text"
                    )
        return ""

    @property
    def config(self) -> dict:
        return {
            "classification_model": self._config.classification_model,
            "reasoning_model": self._config.reasoning_model,
            "default_model": self._config.default_model,
            "rules": [
                {"pattern": r.pattern, "route_to": r.route_to}
                for r in self._config.rules
            ],
        }
