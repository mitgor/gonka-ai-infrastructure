"""
Rate Limiting for Gonka.ai gateway.

Implements sliding-window rate limiting per API key:
- Requests per minute (RPM)
- Tokens per minute (TPM)

Uses in-memory tracking with automatic window expiry.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field

from fastapi import HTTPException


@dataclass
class WindowCounter:
    """Sliding window counter for rate limiting."""
    timestamps: list[float] = field(default_factory=list)
    token_counts: list[tuple[float, int]] = field(default_factory=list)

    def add_request(self, timestamp: float):
        self.timestamps.append(timestamp)

    def add_tokens(self, timestamp: float, count: int):
        self.token_counts.append((timestamp, count))

    def request_count(self, window_seconds: float = 60.0) -> int:
        cutoff = time.time() - window_seconds
        self.timestamps = [t for t in self.timestamps if t > cutoff]
        return len(self.timestamps)

    def token_count(self, window_seconds: float = 60.0) -> int:
        cutoff = time.time() - window_seconds
        self.token_counts = [(t, c) for t, c in self.token_counts if t > cutoff]
        return sum(c for _, c in self.token_counts)


class RateLimiter:
    """Per-key rate limiting with configurable RPM and TPM limits."""

    def __init__(self):
        self._counters: dict[str, WindowCounter] = defaultdict(WindowCounter)

    def check_request(self, api_key: str, rpm_limit: int):
        """Check if request is within rate limits. Raises 429 if exceeded."""
        counter = self._counters[api_key]
        current_rpm = counter.request_count()

        if current_rpm >= rpm_limit:
            retry_after = self._estimate_retry_after(counter)
            raise HTTPException(
                status_code=429,
                detail={
                    "error": {
                        "message": f"Rate limit exceeded: {current_rpm}/{rpm_limit} RPM. Retry after {retry_after}s.",
                        "type": "rate_limit_error",
                        "code": "rate_limit_exceeded",
                    }
                },
                headers={"Retry-After": str(retry_after)},
            )

        counter.add_request(time.time())

    def record_tokens(self, api_key: str, token_count: int):
        """Record token usage for TPM tracking."""
        self._counters[api_key].add_tokens(time.time(), token_count)

    def check_tokens(self, api_key: str, tpm_limit: int):
        """Check if token usage is within limits."""
        counter = self._counters[api_key]
        current_tpm = counter.token_count()

        if current_tpm >= tpm_limit:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": {
                        "message": f"Token rate limit exceeded: {current_tpm}/{tpm_limit} TPM.",
                        "type": "rate_limit_error",
                        "code": "token_rate_limit_exceeded",
                    }
                },
            )

    def get_usage(self, api_key: str) -> dict:
        """Get current usage stats for a key."""
        counter = self._counters[api_key]
        return {
            "rpm_current": counter.request_count(),
            "tpm_current": counter.token_count(),
        }

    def _estimate_retry_after(self, counter: WindowCounter) -> int:
        """Estimate seconds until the oldest request in the window expires."""
        if not counter.timestamps:
            return 1
        oldest = min(counter.timestamps)
        wait = 60.0 - (time.time() - oldest)
        return max(1, int(wait) + 1)
