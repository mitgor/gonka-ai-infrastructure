# Requirements: Gonka Tokenomics

**Defined:** 2026-02-13
**Core Value:** Leadership can tweak assumptions and instantly see the impact on tokenomics health across all dimensions

## v1.2 Requirements

Requirements for Kimi K2.5 Integration & Agent Inference milestone.

### Model Serving

- [ ] **SERV-01**: Kimi K2.5 can be deployed via vLLM with tensor parallelism across multiple GPUs
- [ ] **SERV-02**: vLLM serves OpenAI-compatible `/v1/chat/completions` endpoint for K2.5
- [ ] **SERV-03**: K2.5 tool calling works via vLLM's `kimi_k2` parser
- [ ] **SERV-04**: K2.5 reasoning/thinking mode works via vLLM's `kimi_k2` reasoning parser
- [ ] **SERV-05**: Docker container configuration packages vLLM + K2.5 for GPU node deployment
- [ ] **SERV-06**: Multi-model routing allows serving K2.5 alongside other models (DeepSeek, Llama, Qwen) from a single gateway
- [ ] **SERV-07**: Quantized K2.5 variants (Q4, Q2) can be deployed for cost-optimized tiers
- [ ] **SERV-08**: Health check endpoint reports model status, GPU utilization, and queue depth

### API Gateway

- [ ] **GATE-01**: FastAPI gateway proxies requests to vLLM backends with OpenAI-compatible interface
- [ ] **GATE-02**: API key authentication validates requests before forwarding to model backends
- [ ] **GATE-03**: Rate limiting enforces per-key request limits (configurable per tier)
- [ ] **GATE-04**: Usage metering tracks tokens consumed per API key per model per time period
- [ ] **GATE-05**: Gateway routes requests to correct model backend based on model parameter in request
- [ ] **GATE-06**: Gateway returns standardized error responses matching OpenAI error format
- [ ] **GATE-07**: Gateway supports streaming responses (SSE) for chat completions
- [ ] **GATE-08**: Admin API exposes usage statistics, key management, and model status

### Agent Inference Extensions

- [ ] **AGNT-01**: Session persistence stores conversation history server-side keyed by session ID
- [ ] **AGNT-02**: Memory API allows agents to store and retrieve long-term context (key-value with semantic search)
- [ ] **AGNT-03**: Model tiering auto-routes requests to cheap models for classification and strong models for reasoning based on configurable rules
- [ ] **AGNT-04**: Webhook callbacks notify agents asynchronously when long-running inference completes
- [ ] **AGNT-05**: Usage dashboard shows per-session token consumption, latency, and model usage breakdown
- [ ] **AGNT-06**: Session TTL and cleanup automatically expire inactive sessions after configurable timeout

### Integration Testing

- [ ] **TEST-01**: OpenClaw can connect to Gonka gateway and complete a multi-step agent task using K2.5
- [ ] **TEST-02**: CrewAI multi-agent workflow can execute using Gonka gateway as LLM backend
- [ ] **TEST-03**: LangGraph stateful agent graph can run against Gonka gateway with session persistence
- [ ] **TEST-04**: Integration test suite validates OpenAI API compatibility across all endpoints
- [ ] **TEST-05**: Load test validates gateway handles concurrent requests with proper rate limiting

## Future Requirements

### Additional Models

- **MODL-01**: FLUX.2 image generation endpoint with ComfyUI-compatible API
- **MODL-02**: Wan 2.1 video generation endpoint
- **MODL-03**: DeepSeek R1 distill variants (7B, 14B, 70B)
- **MODL-04**: Llama 4 Scout/Maverick
- **MODL-05**: Qwen3-30B-A3B and Qwen3-235B

### Platform

- **PLAT-01**: GNK token payment integration for API usage
- **PLAT-02**: Host node onboarding and GPU registration
- **PLAT-03**: Geographic load balancing across distributed nodes
- **PLAT-04**: Full agent hosting (Option B -- run agent runtimes on Gonka.ai)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Full agent hosting (Option B) | Too complex for v1.2; start with agent-aware inference (Option C) |
| GNK token payments | Separate milestone; v1.2 uses API keys |
| Image/video model serving (FLUX, Wan) | Separate milestone; focus on LLM serving first |
| Training/fine-tuning infrastructure | Inference-only for v1.2 |
| Mobile SDKs | API-first; SDKs come later |
| Web dashboard UI | Admin API only; UI deferred |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SERV-01 | Phase 10 | Pending |
| SERV-02 | Phase 10 | Pending |
| SERV-03 | Phase 10 | Pending |
| SERV-04 | Phase 10 | Pending |
| SERV-05 | Phase 10 | Pending |
| SERV-06 | Phase 13 | Pending |
| SERV-07 | Phase 13 | Pending |
| SERV-08 | Phase 10 | Pending |
| GATE-01 | Phase 11 | Pending |
| GATE-02 | Phase 11 | Pending |
| GATE-03 | Phase 11 | Pending |
| GATE-04 | Phase 11 | Pending |
| GATE-05 | Phase 11 | Pending |
| GATE-06 | Phase 11 | Pending |
| GATE-07 | Phase 11 | Pending |
| GATE-08 | Phase 13 | Pending |
| AGNT-01 | Phase 12 | Pending |
| AGNT-02 | Phase 12 | Pending |
| AGNT-03 | Phase 13 | Pending |
| AGNT-04 | Phase 12 | Pending |
| AGNT-05 | Phase 13 | Pending |
| AGNT-06 | Phase 12 | Pending |
| TEST-01 | Phase 14 | Pending |
| TEST-02 | Phase 14 | Pending |
| TEST-03 | Phase 14 | Pending |
| TEST-04 | Phase 14 | Pending |
| TEST-05 | Phase 14 | Pending |

**Coverage:**
- v1.2 requirements: 27 total
- Mapped to phases: 27
- Unmapped: 0

---
*Requirements defined: 2026-02-13*
*Last updated: 2026-02-13 after roadmap creation*
