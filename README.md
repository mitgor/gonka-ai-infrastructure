# Gonka.ai Infrastructure

OpenAI-compatible inference gateway for [Gonka.ai](https://gonka.ai) — a decentralized GPU compute network. Serves Kimi K2.5 and other open-source models with agent-aware extensions, session persistence, and multi-model routing.

## Architecture

```
Client (OpenAI SDK / Agent Framework)
  │
  ▼
┌──────────────────────────────────┐
│  API Gateway (FastAPI :9000)     │
│  Auth · Rate Limit · Metering   │
│  Model Routing · SSE Streaming  │
├──────────────────────────────────┤
│  Agent Extensions               │
│  Sessions · Memory · Webhooks   │
│  Model Tiering                  │
├──────────────────────────────────┤
│  Admin API                      │
│  Usage Stats · Key Management   │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│  vLLM Backend(s)                 │
│  K2.5 Full (8 GPU) :8000        │
│  K2.5 Q4  (4 GPU)  :8001        │
│  K2.5 Q2  (2 GPU)  :8002        │
└──────────────────────────────────┘
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start the gateway (requires a vLLM backend running)
uvicorn gateway.main:app --host 0.0.0.0 --port 9000

# Or use Docker for the full stack
cd serving && docker compose --profile k25-full up
```

## Project Structure

```
serving/          # vLLM model serving (launcher, health, Docker)
gateway/          # FastAPI gateway (auth, rate limiting, metering, routing)
agent/            # Agent extensions (sessions, memory, webhooks, tiering)
admin/            # Admin API (usage stats, key management)
config/           # Settings and model registry
tests/            # Integration tests (OpenClaw, CrewAI, LangGraph, load)
docs/             # Strategy and research documents
```

## Key Features

- **OpenAI-compatible API** — drop-in replacement, works with any OpenAI SDK client
- **Kimi K2.5 serving** — vLLM with tensor parallelism, tool calling, thinking mode
- **API key auth** — per-key rate limiting (RPM/TPM) and usage metering
- **Session persistence** — server-side conversation history across requests
- **Memory API** — key-value store with TF-IDF semantic search
- **Model tiering** — auto-route simple requests to cheaper models
- **Webhook callbacks** — async notification for long-running inference
- **Multi-model routing** — serve multiple models behind a single endpoint
- **Quantized variants** — Q4/Q2 tiers for cost-sensitive workloads
- **Admin dashboard** — usage stats, key management, model health

## Agent Framework Compatibility

Tested with:
- **OpenClaw** — multi-step task execution with tool calling
- **CrewAI** — multi-agent workflows with role-based delegation
- **LangGraph** — stateful graph execution with session persistence

## Running Tests

```bash
# Run integration tests (uses mock vLLM backend)
pytest tests/ -v

# Run load tests with Locust
locust -f tests/locustfile.py --host http://localhost:9000
```

## Configuration

Key environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `GONKA_GATEWAY_HOST` | `0.0.0.0` | Gateway bind address |
| `GONKA_GATEWAY_PORT` | `9000` | Gateway port |
| `GONKA_VLLM_BASE_URL` | `http://localhost:8000` | vLLM backend URL |
| `GONKA_DEFAULT_RPM` | `60` | Default rate limit (requests/min) |
| `GONKA_DEFAULT_TPM` | `100000` | Default rate limit (tokens/min) |
| `GONKA_SESSION_TTL` | `3600` | Session timeout (seconds) |
| `GONKA_ADMIN_API_KEY` | (auto-generated) | Admin API authentication key |

See `config/settings.py` for full configuration options and `config/models.yaml` for model registry.

## Documentation

- [Strategy: Kimi K2.5 & Agent Inference](docs/strategy-kimi-k25-agent-inference.md)
- [Research: Model Selection](docs/research-model-selection.md)
