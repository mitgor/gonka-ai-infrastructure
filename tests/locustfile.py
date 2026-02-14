"""
Locust load test for Gonka.ai gateway.

Usage:
    locust -f infrastructure/tests/locustfile.py --host http://localhost:9000

Then open http://localhost:8089 to configure and run the load test.
"""

import json
from locust import HttpUser, task, between

API_KEY = "gk-dev-" + "0" * 48


class GonkaUser(HttpUser):
    wait_time = between(0.5, 2.0)
    headers = {"Authorization": f"Bearer {API_KEY}"}

    @task(5)
    def chat_completion(self):
        self.client.post(
            "/v1/chat/completions",
            headers=self.headers,
            json={
                "model": "kimi-k2.5",
                "messages": [{"role": "user", "content": "Hello, how are you?"}],
                "max_tokens": 50,
            },
        )

    @task(2)
    def chat_with_tools(self):
        self.client.post(
            "/v1/chat/completions",
            headers=self.headers,
            json={
                "model": "kimi-k2.5",
                "messages": [{"role": "user", "content": "Search for GPU prices"}],
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "search",
                            "description": "Search the web",
                            "parameters": {
                                "type": "object",
                                "properties": {"query": {"type": "string"}},
                                "required": ["query"],
                            },
                        },
                    }
                ],
            },
        )

    @task(1)
    def list_models(self):
        self.client.get("/v1/models", headers=self.headers)

    @task(1)
    def health_check(self):
        self.client.get("/health")
