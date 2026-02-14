"""
Webhook Callbacks for Gonka.ai agent inference.

Allows agents to register webhook URLs for async notification
when long-running inference requests complete. Useful for:
- Long-context reasoning that takes >30s
- Background batch processing
- Agent frameworks with async execution patterns
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Optional

import httpx


@dataclass
class WebhookRegistration:
    webhook_id: str
    api_key: str
    url: str
    session_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    max_retries: int = 3
    timeout_seconds: float = 10.0


@dataclass
class WebhookDelivery:
    webhook_id: str
    status: str  # "pending", "delivered", "failed"
    attempts: int = 0
    last_attempt: float = 0.0
    last_status_code: int = 0
    last_error: Optional[str] = None


class WebhookManager:
    """Manages webhook registrations and async delivery."""

    def __init__(self):
        self._registrations: dict[str, WebhookRegistration] = {}
        self._deliveries: dict[str, WebhookDelivery] = {}

    def register(self, webhook_id: str, api_key: str, url: str,
                 session_id: Optional[str] = None,
                 max_retries: int = 3) -> WebhookRegistration:
        """Register a webhook URL for async notifications."""
        reg = WebhookRegistration(
            webhook_id=webhook_id,
            api_key=api_key,
            url=url,
            session_id=session_id,
            max_retries=max_retries,
        )
        self._registrations[webhook_id] = reg
        self._deliveries[webhook_id] = WebhookDelivery(
            webhook_id=webhook_id,
            status="pending",
        )
        return reg

    def unregister(self, webhook_id: str) -> bool:
        """Remove a webhook registration."""
        if webhook_id in self._registrations:
            del self._registrations[webhook_id]
            self._deliveries.pop(webhook_id, None)
            return True
        return False

    async def notify(self, webhook_id: str, payload: dict) -> bool:
        """
        Deliver a webhook notification with retries.
        Returns True if delivered successfully.
        """
        reg = self._registrations.get(webhook_id)
        if not reg:
            return False

        delivery = self._deliveries[webhook_id]

        for attempt in range(reg.max_retries):
            delivery.attempts = attempt + 1
            delivery.last_attempt = time.time()

            try:
                async with httpx.AsyncClient(timeout=reg.timeout_seconds) as client:
                    resp = await client.post(
                        reg.url,
                        json={
                            "webhook_id": webhook_id,
                            "session_id": reg.session_id,
                            "timestamp": time.time(),
                            "data": payload,
                        },
                        headers={
                            "Content-Type": "application/json",
                            "X-Gonka-Webhook-ID": webhook_id,
                        },
                    )
                    delivery.last_status_code = resp.status_code

                    if 200 <= resp.status_code < 300:
                        delivery.status = "delivered"
                        return True

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                delivery.last_error = str(e)

            # Exponential backoff
            if attempt < reg.max_retries - 1:
                await asyncio.sleep(2 ** attempt)

        delivery.status = "failed"
        return False

    async def notify_completion(self, webhook_id: str, response: dict):
        """Notify that an inference request has completed."""
        await self.notify(webhook_id, {
            "type": "inference.completed",
            "response": response,
        })

    def get_status(self, webhook_id: str) -> Optional[dict]:
        """Get delivery status for a webhook."""
        delivery = self._deliveries.get(webhook_id)
        if not delivery:
            return None
        return {
            "webhook_id": delivery.webhook_id,
            "status": delivery.status,
            "attempts": delivery.attempts,
            "last_attempt": delivery.last_attempt,
            "last_status_code": delivery.last_status_code,
            "last_error": delivery.last_error,
        }

    def list_webhooks(self, api_key: str) -> list[dict]:
        """List all webhooks for an API key."""
        return [
            {
                "webhook_id": reg.webhook_id,
                "url": reg.url,
                "session_id": reg.session_id,
                "status": self._deliveries.get(reg.webhook_id, WebhookDelivery(webhook_id="")).status,
                "created_at": reg.created_at,
            }
            for reg in self._registrations.values()
            if reg.api_key == api_key
        ]
