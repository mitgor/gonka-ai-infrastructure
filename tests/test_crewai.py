"""
TEST-02: CrewAI Integration Test.

Validates that a CrewAI multi-agent workflow can execute
using the Gonka.ai gateway as its LLM backend.

CrewAI Pattern:
- Multiple agents with different roles (researcher, writer, etc.)
- Each agent makes separate LLM calls
- Agents pass results to each other
- All through the same OpenAI-compatible API
"""

import httpx
import pytest

from tests.conftest import DEV_API_KEY

BASE_URL = "http://localhost:9000"
HEADERS = {"Authorization": f"Bearer {DEV_API_KEY}"}


class TestCrewAIIntegration:
    """
    Simulate CrewAI's multi-agent interaction patterns.

    CrewAI creates a "crew" of agents, each with:
    - A role/backstory (system message)
    - A task to complete
    - Tools available
    - Ability to delegate to other agents
    """

    @pytest.mark.asyncio
    async def test_researcher_agent(self):
        """Agent 1: Researcher gathers information."""
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            resp = await client.post(
                "/v1/chat/completions",
                headers=HEADERS,
                json={
                    "model": "kimi-k2.5",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a senior research analyst. Your goal is to research topics thoroughly and provide comprehensive analysis.",
                        },
                        {
                            "role": "user",
                            "content": "Research the current state of decentralized GPU compute networks. Focus on market size, key players, and growth trends.",
                        },
                    ],
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["choices"][0]["message"]["role"] == "assistant"
        assert len(data["choices"][0]["message"]["content"]) > 0

    @pytest.mark.asyncio
    async def test_writer_agent(self):
        """Agent 2: Writer creates content from research."""
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            resp = await client.post(
                "/v1/chat/completions",
                headers=HEADERS,
                json={
                    "model": "kimi-k2.5",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a technical content writer. Take research findings and create clear, engaging content.",
                        },
                        {
                            "role": "user",
                            "content": "Based on this research: 'Decentralized GPU networks are growing 428% YoY with 80%+ utilization. Key players: Akash, Render, io.net.' Write a brief market overview.",
                        },
                    ],
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["choices"][0]["message"]["content"]

    @pytest.mark.asyncio
    async def test_multi_agent_workflow(self):
        """
        Full multi-agent workflow:
        1. Researcher researches topic
        2. Writer creates content from research
        3. Editor reviews and refines
        """
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0) as client:
            # Agent 1: Research
            research_resp = await client.post(
                "/v1/chat/completions",
                headers=HEADERS,
                json={
                    "model": "kimi-k2.5",
                    "messages": [
                        {"role": "system", "content": "You are a researcher. Provide key findings in bullet points."},
                        {"role": "user", "content": "Key facts about AI inference costs in 2026"},
                    ],
                    "max_tokens": 200,
                },
            )
            assert research_resp.status_code == 200
            research_output = research_resp.json()["choices"][0]["message"]["content"]

            # Agent 2: Write using research
            write_resp = await client.post(
                "/v1/chat/completions",
                headers=HEADERS,
                json={
                    "model": "kimi-k2.5",
                    "messages": [
                        {"role": "system", "content": "You are a writer. Create a summary from research findings."},
                        {"role": "user", "content": f"Write a summary based on: {research_output}"},
                    ],
                    "max_tokens": 300,
                },
            )
            assert write_resp.status_code == 200
            written_output = write_resp.json()["choices"][0]["message"]["content"]

            # Agent 3: Edit
            edit_resp = await client.post(
                "/v1/chat/completions",
                headers=HEADERS,
                json={
                    "model": "kimi-k2.5",
                    "messages": [
                        {"role": "system", "content": "You are an editor. Review and improve the text. Output the final version."},
                        {"role": "user", "content": f"Review and polish: {written_output}"},
                    ],
                    "max_tokens": 300,
                },
            )
            assert edit_resp.status_code == 200

        # All three agents completed successfully
        final_output = edit_resp.json()["choices"][0]["message"]["content"]
        assert len(final_output) > 0

    @pytest.mark.asyncio
    async def test_crewai_with_tool_calling(self):
        """CrewAI agent using tools through Gonka gateway."""
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            resp = await client.post(
                "/v1/chat/completions",
                headers=HEADERS,
                json={
                    "model": "kimi-k2.5",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a data analyst with access to tools.",
                        },
                        {
                            "role": "user",
                            "content": "Search for the latest GPU pricing data",
                        },
                    ],
                    "tools": [
                        {
                            "type": "function",
                            "function": {
                                "name": "search_web",
                                "description": "Search the web",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "query": {"type": "string"},
                                    },
                                    "required": ["query"],
                                },
                            },
                        }
                    ],
                },
            )

        assert resp.status_code == 200
