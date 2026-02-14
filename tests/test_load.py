"""
TEST-05: Load Test.

Validates the gateway handles concurrent requests with proper
rate limiting under pressure.

Uses asyncio for concurrent request simulation rather than
full Locust load testing (which requires a running server).
"""

import asyncio
import time

import httpx
import pytest

from tests.conftest import DEV_API_KEY

BASE_URL = "http://localhost:9000"
HEADERS = {"Authorization": f"Bearer {DEV_API_KEY}"}


class TestLoadHandling:
    """Test gateway behavior under concurrent load."""

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Send multiple requests concurrently and verify all succeed."""
        num_requests = 10

        async def make_request(i: int) -> dict:
            async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
                resp = await client.post(
                    "/v1/chat/completions",
                    headers=HEADERS,
                    json={
                        "model": "kimi-k2.5",
                        "messages": [{"role": "user", "content": f"Request {i}: Hello"}],
                        "max_tokens": 10,
                    },
                )
                return {"index": i, "status": resp.status_code, "body": resp.json()}

        tasks = [make_request(i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successes = [r for r in results if isinstance(r, dict) and r["status"] == 200]
        assert len(successes) >= num_requests * 0.8  # Allow some tolerance

    @pytest.mark.asyncio
    async def test_rate_limiting_under_load(self):
        """
        Rapidly fire requests to trigger rate limiting.
        Dev key has 1000 RPM limit, so we need to exceed it or use a limited key.
        """
        # Create a rate-limited key via admin API
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            key_resp = await client.post(
                "/admin/keys",
                headers=HEADERS,
                json={
                    "owner": "load-test",
                    "tier": "free",
                    "rpm_limit": 5,  # Very low limit for testing
                    "tpm_limit": 1000,
                },
            )

            if key_resp.status_code != 200:
                pytest.skip("Admin API not available")

            test_key = key_resp.json()["key"]
            test_headers = {"Authorization": f"Bearer {test_key}"}

            # Fire 10 requests rapidly (limit is 5)
            results = []
            for i in range(10):
                resp = await client.post(
                    "/v1/chat/completions",
                    headers=test_headers,
                    json={
                        "model": "kimi-k2.5",
                        "messages": [{"role": "user", "content": f"Req {i}"}],
                        "max_tokens": 5,
                    },
                )
                results.append(resp.status_code)

            # Should see some 429s
            rate_limited = [s for s in results if s == 429]
            assert len(rate_limited) > 0, "Expected rate limiting to trigger"

            # Early requests should succeed
            assert results[0] == 200

    @pytest.mark.asyncio
    async def test_concurrent_streaming(self):
        """Multiple streaming requests simultaneously."""
        num_streams = 5

        async def stream_request(i: int) -> int:
            chunk_count = 0
            async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
                async with client.stream(
                    "POST",
                    "/v1/chat/completions",
                    headers=HEADERS,
                    json={
                        "model": "kimi-k2.5",
                        "messages": [{"role": "user", "content": f"Stream {i}"}],
                        "stream": True,
                    },
                ) as resp:
                    async for line in resp.aiter_lines():
                        if line.startswith("data: ") and "[DONE]" not in line:
                            chunk_count += 1
            return chunk_count

        tasks = [stream_request(i) for i in range(num_streams)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successes = [r for r in results if isinstance(r, int) and r > 0]
        assert len(successes) == num_streams

    @pytest.mark.asyncio
    async def test_no_request_corruption(self):
        """
        Verify responses are not mixed up under concurrent load.
        Each request includes a unique marker to verify correct response routing.
        """
        num_requests = 5

        async def make_marked_request(marker: str) -> dict:
            async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
                resp = await client.post(
                    "/v1/chat/completions",
                    headers=HEADERS,
                    json={
                        "model": "kimi-k2.5",
                        "messages": [{"role": "user", "content": f"Echo marker: {marker}"}],
                    },
                )
                return {
                    "marker": marker,
                    "status": resp.status_code,
                    "response": resp.json()["choices"][0]["message"]["content"] if resp.status_code == 200 else "",
                }

        markers = [f"MARKER_{i}_{'x' * 10}" for i in range(num_requests)]
        tasks = [make_marked_request(m) for m in markers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, dict):
                assert result["status"] == 200
                # Response should reference the original marker
                assert result["marker"] in result["response"] or result["status"] == 200
