"""
TEST-04: OpenAI API Compatibility Test Suite.

Validates that the Gonka.ai gateway is fully compatible with
OpenAI's API format across all endpoints.
"""

import json
import time

import httpx
import pytest

from tests.conftest import DEV_API_KEY

BASE_URL = "http://localhost:9000"
HEADERS = {"Authorization": f"Bearer {DEV_API_KEY}"}


class TestModelsEndpoint:
    """Test /v1/models endpoint."""

    @pytest.mark.asyncio
    async def test_list_models_returns_correct_format(self):
        async with httpx.AsyncClient(base_url=BASE_URL) as client:
            resp = await client.get("/v1/models", headers=HEADERS)

        assert resp.status_code == 200
        data = resp.json()
        assert data["object"] == "list"
        assert isinstance(data["data"], list)

        if data["data"]:
            model = data["data"][0]
            assert "id" in model
            assert model["object"] == "model"
            assert "owned_by" in model


class TestChatCompletions:
    """Test /v1/chat/completions endpoint."""

    @pytest.mark.asyncio
    async def test_basic_chat_completion(self):
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            resp = await client.post(
                "/v1/chat/completions",
                headers=HEADERS,
                json={
                    "model": "kimi-k2.5",
                    "messages": [
                        {"role": "user", "content": "Hello, what is 2+2?"}
                    ],
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["object"] == "chat.completion"
        assert len(data["choices"]) > 0
        assert data["choices"][0]["message"]["role"] == "assistant"
        assert isinstance(data["choices"][0]["message"]["content"], str)
        assert "usage" in data
        assert "prompt_tokens" in data["usage"]
        assert "completion_tokens" in data["usage"]
        assert "total_tokens" in data["usage"]

    @pytest.mark.asyncio
    async def test_tool_calling(self):
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            resp = await client.post(
                "/v1/chat/completions",
                headers=HEADERS,
                json={
                    "model": "kimi-k2.5",
                    "messages": [
                        {"role": "user", "content": "What's the weather in London?"}
                    ],
                    "tools": [
                        {
                            "type": "function",
                            "function": {
                                "name": "get_weather",
                                "description": "Get weather for a location",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "location": {"type": "string"},
                                    },
                                    "required": ["location"],
                                },
                            },
                        }
                    ],
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        choice = data["choices"][0]
        assert choice["finish_reason"] == "tool_calls"
        assert choice["message"]["tool_calls"] is not None
        assert len(choice["message"]["tool_calls"]) > 0

        tool_call = choice["message"]["tool_calls"][0]
        assert tool_call["type"] == "function"
        assert "name" in tool_call["function"]
        assert "arguments" in tool_call["function"]

    @pytest.mark.asyncio
    async def test_streaming(self):
        chunks = []
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            async with client.stream(
                "POST",
                "/v1/chat/completions",
                headers=HEADERS,
                json={
                    "model": "kimi-k2.5",
                    "messages": [{"role": "user", "content": "Count to 3"}],
                    "stream": True,
                },
            ) as resp:
                assert resp.status_code == 200
                assert resp.headers["content-type"].startswith("text/event-stream")

                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        chunk = json.loads(data_str)
                        chunks.append(chunk)

        assert len(chunks) > 0
        assert chunks[0]["object"] == "chat.completion.chunk"
        assert "delta" in chunks[0]["choices"][0]


class TestAuthentication:
    """Test authentication behavior."""

    @pytest.mark.asyncio
    async def test_missing_api_key_returns_401(self):
        async with httpx.AsyncClient(base_url=BASE_URL) as client:
            resp = await client.post(
                "/v1/chat/completions",
                json={
                    "model": "kimi-k2.5",
                    "messages": [{"role": "user", "content": "test"}],
                },
            )

        assert resp.status_code == 401
        data = resp.json()
        assert "error" in data
        assert data["error"]["type"] == "invalid_request_error"

    @pytest.mark.asyncio
    async def test_invalid_api_key_returns_401(self):
        async with httpx.AsyncClient(base_url=BASE_URL) as client:
            resp = await client.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer invalid-key-12345"},
                json={
                    "model": "kimi-k2.5",
                    "messages": [{"role": "user", "content": "test"}],
                },
            )

        assert resp.status_code == 401


class TestErrorFormat:
    """Test error response format matches OpenAI."""

    @pytest.mark.asyncio
    async def test_invalid_model_returns_openai_error(self):
        async with httpx.AsyncClient(base_url=BASE_URL) as client:
            resp = await client.post(
                "/v1/chat/completions",
                headers=HEADERS,
                json={
                    "model": "nonexistent-model",
                    "messages": [{"role": "user", "content": "test"}],
                },
            )

        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data
        assert "message" in data["error"]
        assert "type" in data["error"]
        assert "code" in data["error"]

    @pytest.mark.asyncio
    async def test_invalid_json_returns_400(self):
        async with httpx.AsyncClient(base_url=BASE_URL) as client:
            resp = await client.post(
                "/v1/chat/completions",
                headers={**HEADERS, "Content-Type": "application/json"},
                content=b"not valid json",
            )

        assert resp.status_code == 400
