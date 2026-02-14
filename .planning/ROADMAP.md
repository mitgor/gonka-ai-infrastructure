# Roadmap: Gonka Tokenomics

## Milestones

- v1.0 Tokenomics Research & Optimization (shipped 2026-02-05)
- v1.1 Economic Modeling (shipped 2026-02-07)
- **v1.2 Kimi K2.5 Integration & Agent Inference** (in progress)

<details>
<summary>v1.0 Tokenomics Research (Phases 1) - SHIPPED 2026-02-05</summary>

Phase 1: 8 plans across 3 waves. See MILESTONES.md for details.

</details>

<details>
<summary>v1.1 Economic Modeling (Phases 1-9) - SHIPPED 2026-02-07</summary>

Phases 1-9: 21 plans total. See MILESTONES.md for details.

</details>

## v1.2 Kimi K2.5 Integration & Agent Inference

**Milestone Goal:** Build infrastructure code to deploy Kimi K2.5 on Gonka.ai as an OpenAI-compatible inference endpoint with agent-aware extensions, API gateway, and validated integration with major agent frameworks.

**Phase Numbering:** Continues from v1.1 (phases 1-9). v1.2 starts at phase 10.

- [x] **Phase 10: K2.5 Model Serving** - Deploy Kimi K2.5 via vLLM with OpenAI-compatible API, tool calling, thinking mode, and Docker packaging
- [x] **Phase 11: API Gateway** - FastAPI gateway with auth, rate limiting, usage metering, model routing, streaming, and error handling
- [x] **Phase 12: Agent Inference Extensions** - Session persistence, memory API, model tiering, webhook callbacks, and session lifecycle
- [x] **Phase 13: Multi-Model & Admin** - Multi-model routing, quantized variants, admin API, and usage dashboard
- [x] **Phase 14: Integration Testing** - End-to-end validation with OpenClaw, CrewAI, LangGraph, API compatibility suite, and load testing

## Phase Details

### Phase 10: K2.5 Model Serving
**Goal**: A developer can send chat completion requests to a running K2.5 instance and receive responses through an OpenAI-compatible API, including tool calling and reasoning mode
**Depends on**: Nothing (first phase of v1.2)
**Requirements**: SERV-01, SERV-02, SERV-03, SERV-04, SERV-05, SERV-08
**Success Criteria** (what must be TRUE):
  1. A developer can start the vLLM server with K2.5 and it serves requests across multiple GPUs via tensor parallelism
  2. A developer can hit `/v1/chat/completions` with a standard OpenAI client library and get valid K2.5 responses
  3. A developer can invoke K2.5 tool calling (function calling) through the API and receive structured tool call responses
  4. A developer can enable K2.5 thinking/reasoning mode and receive chain-of-thought responses
  5. A developer can build and run the Docker container on a GPU node and the health endpoint reports model status, GPU utilization, and queue depth
**Plans**: TBD

Plans:
- [ ] 10-01: TBD
- [ ] 10-02: TBD
- [ ] 10-03: TBD

### Phase 11: API Gateway
**Goal**: All inference requests flow through a FastAPI gateway that authenticates, rate limits, meters usage, routes to backends, streams responses, and returns standardized errors
**Depends on**: Phase 10 (gateway needs a working model backend to proxy to)
**Requirements**: GATE-01, GATE-02, GATE-03, GATE-04, GATE-05, GATE-06, GATE-07
**Success Criteria** (what must be TRUE):
  1. A developer can send requests to the gateway using an OpenAI client library and get responses proxied from the vLLM backend
  2. Requests without a valid API key are rejected; requests with a valid key are forwarded to the correct model backend
  3. A developer who exceeds their rate limit receives a 429 response; usage tokens are tracked per key per model per time period
  4. A developer can stream chat completions via SSE through the gateway with no buffering issues
  5. Gateway error responses match OpenAI's error format (type, message, code fields)
**Plans**: TBD

Plans:
- [ ] 11-01: TBD
- [ ] 11-02: TBD
- [ ] 11-03: TBD

### Phase 12: Agent Inference Extensions
**Goal**: Agent frameworks can use Gonka as a stateful inference backend with server-side conversation memory, long-term context storage, and automatic session lifecycle management
**Depends on**: Phase 11 (agent extensions sit on top of the gateway)
**Requirements**: AGNT-01, AGNT-02, AGNT-04, AGNT-06
**Success Criteria** (what must be TRUE):
  1. An agent can send requests with a session ID and the server maintains conversation history across multiple requests without the agent re-sending context
  2. An agent can store and retrieve long-term context via the memory API using key-value pairs with semantic search
  3. An agent can register a webhook URL and receive async notification when a long-running inference request completes
  4. Inactive sessions are automatically expired and cleaned up after a configurable TTL, freeing server resources
**Plans**: TBD

Plans:
- [ ] 12-01: TBD
- [ ] 12-02: TBD

### Phase 13: Multi-Model & Admin
**Goal**: The platform supports multiple models behind a single gateway with intelligent routing, cost-optimized quantized tiers, and admin visibility into usage and operations
**Depends on**: Phase 11 (multi-model routing extends gateway), Phase 12 (model tiering uses agent context)
**Requirements**: SERV-06, SERV-07, AGNT-03, AGNT-05, GATE-08
**Success Criteria** (what must be TRUE):
  1. A developer can serve K2.5 alongside other models (DeepSeek, Llama, Qwen) and requests are routed to the correct backend based on the model parameter
  2. Quantized K2.5 variants (Q4, Q2) can be deployed and served as separate model options for cost-sensitive workloads
  3. Classification/simple requests are auto-routed to cheaper models while reasoning requests go to K2.5, based on configurable rules
  4. An admin can view per-session token consumption, latency, model usage breakdown, and manage API keys through the admin API
**Plans**: TBD

Plans:
- [ ] 13-01: TBD
- [ ] 13-02: TBD

### Phase 14: Integration Testing
**Goal**: The complete Gonka inference stack is validated end-to-end with real agent frameworks, API compatibility tests, and load testing
**Depends on**: Phase 10, 11, 12, 13 (tests exercise the full stack)
**Requirements**: TEST-01, TEST-02, TEST-03, TEST-04, TEST-05
**Success Criteria** (what must be TRUE):
  1. An OpenClaw agent can connect to the Gonka gateway and complete a multi-step task using K2.5 as its LLM backend
  2. A CrewAI multi-agent workflow executes successfully using the Gonka gateway as its LLM provider
  3. A LangGraph stateful agent graph runs against the Gonka gateway, using session persistence to maintain state across steps
  4. An automated test suite confirms OpenAI API compatibility across chat completions, streaming, tool calling, and error handling
  5. A load test confirms the gateway handles concurrent requests correctly, rate limiting fires under load, and no requests are dropped or corrupted
**Plans**: TBD

Plans:
- [ ] 14-01: TBD
- [ ] 14-02: TBD

## Progress

**Execution Order:** 10 -> 11 -> 12 -> 13 -> 14

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 10. K2.5 Model Serving | v1.2 | 1/1 | Complete | 2026-02-13 |
| 11. API Gateway | v1.2 | 1/1 | Complete | 2026-02-13 |
| 12. Agent Inference Extensions | v1.2 | 1/1 | Complete | 2026-02-13 |
| 13. Multi-Model & Admin | v1.2 | 1/1 | Complete | 2026-02-13 |
| 14. Integration Testing | v1.2 | 1/1 | Complete | 2026-02-13 |
