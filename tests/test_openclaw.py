"""
TEST-01: OpenClaw Integration Test.

Validates that OpenClaw can connect to the Gonka.ai gateway
and complete a multi-step agent task using K2.5 as its LLM backend.

OpenClaw uses OpenAI-compatible endpoints, so this test simulates
the request patterns OpenClaw makes.
"""

import json

import httpx
import pytest

from tests.conftest import DEV_API_KEY

BASE_URL = "http://localhost:9000"
HEADERS = {"Authorization": f"Bearer {DEV_API_KEY}"}


class TestOpenClawIntegration:
    """
    Simulate OpenClaw's interaction patterns with the Gonka gateway.

    OpenClaw's Agent Runner:
    1. Receives message via channel (Telegram, Slack, etc.)
    2. Classifies intent (cheap model)
    3. Plans execution (strong model)
    4. Executes tools (function calling)
    5. Returns formatted response
    """

    @pytest.mark.asyncio
    async def test_openclaw_intent_classification(self):
        """
        Step 1: OpenClaw classifies the user's intent.
        Uses a lightweight request to determine next action.
        """
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            resp = await client.post(
                "/v1/chat/completions",
                headers=HEADERS,
                json={
                    "model": "kimi-k2.5",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an intent classifier. Classify the user message into: search, code, chat, file_operation. Respond with just the category.",
                        },
                        {
                            "role": "user",
                            "content": "Find all Python files that import FastAPI",
                        },
                    ],
                    "max_tokens": 10,
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["choices"][0]["message"]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_openclaw_tool_execution(self):
        """
        Step 2: OpenClaw uses tool calling to execute shell commands.
        This simulates OpenClaw's controlled tool execution pattern.
        """
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            resp = await client.post(
                "/v1/chat/completions",
                headers=HEADERS,
                json={
                    "model": "kimi-k2.5",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an AI assistant with access to tools. Use the shell tool to find Python files.",
                        },
                        {
                            "role": "user",
                            "content": "Find all Python files that import FastAPI",
                        },
                    ],
                    "tools": [
                        {
                            "type": "function",
                            "function": {
                                "name": "shell",
                                "description": "Execute a shell command",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "command": {
                                            "type": "string",
                                            "description": "The shell command to execute",
                                        },
                                    },
                                    "required": ["command"],
                                },
                            },
                        }
                    ],
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        choice = data["choices"][0]
        # OpenClaw expects tool_calls or content
        assert choice["message"]["role"] == "assistant"
        assert (
            choice["message"].get("tool_calls") is not None
            or choice["message"].get("content") is not None
        )

    @pytest.mark.asyncio
    async def test_openclaw_multi_turn_with_session(self):
        """
        Step 3: OpenClaw maintains conversation context across turns.
        Uses X-Gonka-Session-ID for server-side history.
        """
        session_id = "openclaw-test-session-001"
        session_headers = {**HEADERS, "X-Gonka-Session-ID": session_id}

        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            # Turn 1: Initial request
            resp1 = await client.post(
                "/v1/chat/completions",
                headers=session_headers,
                json={
                    "model": "kimi-k2.5",
                    "messages": [
                        {"role": "user", "content": "My name is Alice."},
                    ],
                },
            )
            assert resp1.status_code == 200

            # Turn 2: Follow-up that requires context
            resp2 = await client.post(
                "/v1/chat/completions",
                headers=session_headers,
                json={
                    "model": "kimi-k2.5",
                    "messages": [
                        {"role": "user", "content": "What is my name?"},
                    ],
                },
            )
            assert resp2.status_code == 200

    @pytest.mark.asyncio
    async def test_openclaw_streaming_response(self):
        """
        Step 4: OpenClaw can stream responses for real-time display.
        """
        chunks_received = 0
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            async with client.stream(
                "POST",
                "/v1/chat/completions",
                headers=HEADERS,
                json={
                    "model": "kimi-k2.5",
                    "messages": [
                        {"role": "user", "content": "Write a haiku about code"},
                    ],
                    "stream": True,
                },
            ) as resp:
                assert resp.status_code == 200
                async for line in resp.aiter_lines():
                    if line.startswith("data: ") and line[6:].strip() != "[DONE]":
                        chunks_received += 1

        assert chunks_received > 0

    @pytest.mark.asyncio
    async def test_openclaw_full_workflow(self):
        """
        Full end-to-end: classify -> plan -> execute -> respond.
        Simulates a complete OpenClaw agent interaction.
        """
        session_id = "openclaw-e2e-test"
        session_headers = {**HEADERS, "X-Gonka-Session-ID": session_id}

        async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0) as client:
            # 1. Classify
            classify_resp = await client.post(
                "/v1/chat/completions",
                headers=session_headers,
                json={
                    "model": "kimi-k2.5",
                    "messages": [
                        {"role": "system", "content": "Classify: search, code, chat"},
                        {"role": "user", "content": "Analyze my codebase structure"},
                    ],
                    "max_tokens": 10,
                },
            )
            assert classify_resp.status_code == 200

            # 2. Plan with tools
            plan_resp = await client.post(
                "/v1/chat/completions",
                headers=session_headers,
                json={
                    "model": "kimi-k2.5",
                    "messages": [
                        {"role": "system", "content": "Plan the task execution using available tools."},
                        {"role": "user", "content": "Analyze the codebase structure"},
                    ],
                    "tools": [
                        {
                            "type": "function",
                            "function": {
                                "name": "shell",
                                "description": "Execute shell command",
                                "parameters": {
                                    "type": "object",
                                    "properties": {"command": {"type": "string"}},
                                    "required": ["command"],
                                },
                            },
                        },
                        {
                            "type": "function",
                            "function": {
                                "name": "read_file",
                                "description": "Read a file",
                                "parameters": {
                                    "type": "object",
                                    "properties": {"path": {"type": "string"}},
                                    "required": ["path"],
                                },
                            },
                        },
                    ],
                },
            )
            assert plan_resp.status_code == 200

            # 3. Verify session state
            session_resp = await client.get(
                f"/v1/sessions/{session_id}",
                headers=HEADERS,
            )
            assert session_resp.status_code == 200
            session_data = session_resp.json()
            assert session_data["message_count"] > 0
