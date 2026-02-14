"""
TEST-03: LangGraph Integration Test.

Validates that a LangGraph stateful agent graph can run
against the Gonka.ai gateway with session persistence.

LangGraph Pattern:
- Graph of nodes (LLM calls, tools, conditionals)
- Stateful execution across nodes
- Checkpointing and resumability
- All through OpenAI-compatible chat completions
"""

import httpx
import pytest

from tests.conftest import DEV_API_KEY

BASE_URL = "http://localhost:9000"
HEADERS = {"Authorization": f"Bearer {DEV_API_KEY}"}


class TestLangGraphIntegration:
    """
    Simulate LangGraph's stateful graph execution patterns.

    LangGraph builds a graph where:
    - Each node is an LLM call or tool execution
    - State is passed between nodes
    - The graph can branch based on LLM output
    - Session persistence maintains state across API calls
    """

    @pytest.mark.asyncio
    async def test_graph_node_llm_call(self):
        """Single graph node: LLM decision point."""
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            resp = await client.post(
                "/v1/chat/completions",
                headers=HEADERS,
                json={
                    "model": "kimi-k2.5",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a routing agent. Decide next action: 'search', 'respond', or 'clarify'. Output ONLY the action word.",
                        },
                        {
                            "role": "user",
                            "content": "What GPU models does Gonka.ai support?",
                        },
                    ],
                    "max_tokens": 5,
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["choices"][0]["message"]["content"]

    @pytest.mark.asyncio
    async def test_stateful_graph_with_sessions(self):
        """
        Multi-node graph execution using session persistence.

        Graph: classify -> search -> synthesize -> respond
        Each node is a separate API call with the same session ID.
        """
        session_id = "langgraph-test-001"
        session_headers = {**HEADERS, "X-Gonka-Session-ID": session_id}

        async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0) as client:
            # Create session with graph state
            await client.post(
                "/v1/sessions",
                headers=HEADERS,
                json={
                    "session_id": session_id,
                    "system_message": "You are part of a multi-step reasoning graph. Each step builds on previous context.",
                    "metadata": {"graph": "search-and-respond", "step": 0},
                },
            )

            # Node 1: Classify intent
            node1 = await client.post(
                "/v1/chat/completions",
                headers=session_headers,
                json={
                    "model": "kimi-k2.5",
                    "messages": [
                        {"role": "user", "content": "What are the best GPU models for running Kimi K2.5?"},
                    ],
                    "max_tokens": 50,
                },
            )
            assert node1.status_code == 200

            # Node 2: Generate search queries based on classification
            node2 = await client.post(
                "/v1/chat/completions",
                headers=session_headers,
                json={
                    "model": "kimi-k2.5",
                    "messages": [
                        {"role": "user", "content": "Based on the previous question, generate 3 search queries to find the answer."},
                    ],
                    "max_tokens": 100,
                },
            )
            assert node2.status_code == 200

            # Node 3: Synthesize and respond
            node3 = await client.post(
                "/v1/chat/completions",
                headers=session_headers,
                json={
                    "model": "kimi-k2.5",
                    "messages": [
                        {"role": "user", "content": "Synthesize everything discussed and provide a final answer."},
                    ],
                    "max_tokens": 200,
                },
            )
            assert node3.status_code == 200

            # Verify session accumulated state
            session_resp = await client.get(
                f"/v1/sessions/{session_id}",
                headers=HEADERS,
            )
            assert session_resp.status_code == 200
            session_data = session_resp.json()
            # Should have system + 3 user messages + 3 assistant responses = 7+ messages
            assert session_data["message_count"] >= 6

    @pytest.mark.asyncio
    async def test_graph_with_memory_checkpoint(self):
        """
        LangGraph uses memory API for checkpointing graph state.
        """
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            # Save graph state to memory
            save_resp = await client.post(
                "/v1/memory",
                headers=HEADERS,
                json={
                    "key": "graph-state-001",
                    "value": '{"step": 2, "results": ["gpu-a100", "gpu-h200"], "status": "in_progress"}',
                    "namespace": "langgraph",
                    "metadata": {"graph_id": "search-graph", "checkpoint": 2},
                },
            )
            assert save_resp.status_code == 200

            # Retrieve checkpoint
            get_resp = await client.get(
                "/v1/memory/graph-state-001?namespace=langgraph",
                headers=HEADERS,
            )
            assert get_resp.status_code == 200
            data = get_resp.json()
            assert "gpu-a100" in data["value"]

            # Search for related state
            search_resp = await client.post(
                "/v1/memory/search",
                headers=HEADERS,
                json={
                    "query": "graph state gpu search",
                    "namespace": "langgraph",
                    "limit": 5,
                },
            )
            assert search_resp.status_code == 200
            results = search_resp.json()["results"]
            assert len(results) > 0

    @pytest.mark.asyncio
    async def test_graph_branching_with_tool_calls(self):
        """
        LangGraph conditional branching via tool calls.
        The model decides which tool (graph branch) to take.
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
                            "content": "Choose the appropriate tool based on the user's request.",
                        },
                        {"role": "user", "content": "I need to look up pricing information"},
                    ],
                    "tools": [
                        {
                            "type": "function",
                            "function": {
                                "name": "search_docs",
                                "description": "Search documentation",
                                "parameters": {
                                    "type": "object",
                                    "properties": {"query": {"type": "string"}},
                                    "required": ["query"],
                                },
                            },
                        },
                        {
                            "type": "function",
                            "function": {
                                "name": "query_database",
                                "description": "Query pricing database",
                                "parameters": {
                                    "type": "object",
                                    "properties": {"table": {"type": "string"}, "filter": {"type": "string"}},
                                    "required": ["table"],
                                },
                            },
                        },
                    ],
                },
            )

        assert resp.status_code == 200
        # LangGraph expects either tool_calls (to branch) or content (to respond)
        choice = resp.json()["choices"][0]
        assert choice["message"]["role"] == "assistant"
