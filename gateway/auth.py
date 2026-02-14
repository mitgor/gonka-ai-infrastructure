"""
API Key Authentication for Gonka.ai gateway.

Validates Bearer tokens against stored API keys.
Keys are stored in a JSON file with per-key metadata (tier, rate limits, owner).
"""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, Request


@dataclass
class APIKey:
    key: str
    owner: str
    tier: str = "standard"  # "free", "standard", "premium"
    rpm_limit: int = 60
    tpm_limit: int = 100_000
    created_at: float = field(default_factory=time.time)
    active: bool = True


class AuthManager:
    """Manages API keys and validates requests."""

    def __init__(self, keys_file: str = ""):
        self._keys: dict[str, APIKey] = {}
        self._keys_file = keys_file
        if keys_file and Path(keys_file).exists():
            self._load_keys(keys_file)

    def _load_keys(self, filepath: str):
        with open(filepath) as f:
            data = json.load(f)
        for entry in data.get("keys", []):
            key = APIKey(**entry)
            self._keys[key.key] = key

    def save_keys(self, filepath: str = ""):
        filepath = filepath or self._keys_file
        if not filepath:
            return
        data = {
            "keys": [
                {
                    "key": k.key,
                    "owner": k.owner,
                    "tier": k.tier,
                    "rpm_limit": k.rpm_limit,
                    "tpm_limit": k.tpm_limit,
                    "created_at": k.created_at,
                    "active": k.active,
                }
                for k in self._keys.values()
            ]
        }
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def add_key(self, key: str, owner: str, tier: str = "standard",
                rpm_limit: int = 60, tpm_limit: int = 100_000) -> APIKey:
        api_key = APIKey(
            key=key, owner=owner, tier=tier,
            rpm_limit=rpm_limit, tpm_limit=tpm_limit,
        )
        self._keys[key] = api_key
        self.save_keys()
        return api_key

    def revoke_key(self, key: str) -> bool:
        if key in self._keys:
            self._keys[key].active = False
            self.save_keys()
            return True
        return False

    def validate(self, key: str) -> Optional[APIKey]:
        """Validate an API key. Returns APIKey if valid, None otherwise."""
        api_key = self._keys.get(key)
        if api_key and api_key.active:
            return api_key
        return None

    def list_keys(self) -> list[dict]:
        return [
            {
                "key": k.key[:8] + "..." + k.key[-4:],
                "owner": k.owner,
                "tier": k.tier,
                "active": k.active,
                "created_at": k.created_at,
            }
            for k in self._keys.values()
        ]

    @property
    def key_count(self) -> int:
        return len(self._keys)


def extract_api_key(request: Request) -> str:
    """Extract API key from Authorization header."""
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    raise HTTPException(
        status_code=401,
        detail={
            "error": {
                "message": "Missing or invalid API key. Provide via: Authorization: Bearer <key>",
                "type": "invalid_request_error",
                "code": "invalid_api_key",
            }
        },
    )
