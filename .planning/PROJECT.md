# Gonka Tokenomics

## What This Is

Economic modeling tools for Gonka Network's tokenomics. Python scripts generate 5 Excel workbooks (.xlsx) with 70 adjustable parameters, enabling leadership to compare scenarios and make data-driven implementation decisions across emissions, pricing, host profitability, fee transitions, and treasury management. Built on the research foundation from v1.0 (10 prioritized recommendations covering POL, real yield, veGNK, fee transition, GPU economics, and more).

## Core Value

Leadership can tweak assumptions and instantly see the impact on tokenomics health across all dimensions (price, emissions, host profitability, treasury).

## Current Milestone: v1.2 Kimi K2.5 Integration & Agent Inference

**Goal:** Build the infrastructure code to deploy Kimi K2.5 on Gonka.ai as an OpenAI-compatible inference endpoint with agent-aware extensions.

**Target features:**
- vLLM-based Kimi K2.5 serving with OpenAI-compatible API
- API gateway with auth, rate limiting, and usage metering
- Agent-aware inference extensions (session persistence, model tiering)
- Docker/container deployment configuration
- Integration with agent frameworks (OpenClaw, CrewAI, LangGraph)

## Requirements

### Validated

- Research: 10 prioritized tokenomics recommendations with specific parameters -- v1.0
- Research: 5 deep research documents (POL, real yield, veGNK, fee transition, GPU economics) -- v1.0
- Research: Updated synthesis documents (Macro Research v2.0, Deep Analysis v3.0, Explained v3.0) -- v1.0
- Research: Capstone Fine-Tuning Recommendations document -- v1.0
- Python scripts (openpyxl) that generate formatted .xlsx workbooks -- v1.1
- Token price scenario model with multiple growth trajectories -- v1.1
- Emission vs fee transition simulation with crossover analysis -- v1.1
- Host profitability model (ROI under varying GNK prices, network sizes, fee structures) -- v1.1
- Treasury & POL simulation (Community Pool depletion, POL returns, buyback impact) -- v1.1
- Master unified workbook with linked tabs and adjustable assumptions -- v1.1
- Standalone summary workbooks for each modeling area -- v1.1
- All models parameterized from v1.0 research (specific numbers, not placeholders) -- v1.1

### Active

- [ ] Kimi K2.5 inference serving via vLLM with OpenAI-compatible API
- [ ] API gateway (auth, rate limiting, usage metering, multi-model routing)
- [ ] Agent-aware inference extensions (session persistence, memory API, model tiering)
- [ ] Docker/container deployment configuration for GPU nodes
- [ ] Integration testing with OpenClaw, CrewAI, LangGraph agent frameworks

### Out of Scope

- Smart contract implementation -- deferred to future milestone
- Governance proposal drafting -- deferred to future milestone
- Real-time dashboards or web interfaces -- spreadsheets are the delivery format
- Monte Carlo / stochastic simulation -- deterministic scenario models for v1.1
- Backtesting against historical data -- forward-looking projections only

## Context

- **v1.0 research provides all input parameters** -- emission decay rate (-0.000475), revenue splits (70/20/5/5), POL allocation (22M GNK), veGNK lock ranges, fee transition scenarios, GPU pricing trajectories, etc.
- **v1.1 delivered 5 Excel workbooks** -- 1 master (8 tabs) + 4 standalone, 70 parameters with confidence levels, cell protection, print-ready, cross-platform validated
- **v1.2 expands from modeling to infrastructure** -- building actual deployment code for Gonka.ai platform
- **Primary audience:** Gonka founders/leadership (strategy) + developers (integration code)
- **Tech stack (modeling):** Python 3.x with openpyxl==3.1.5 (sole dependency), 5,643 LOC across 19 source files
- **Tech stack (v1.2 infrastructure):** Python (FastAPI), vLLM, Docker, OpenAI-compatible API
- **Kimi K2.5:** 1T param MoE model, requires 4x H200 for production, vLLM v0.15.0+, OpenAI-compatible
- **Agent inference landscape:** OpenClaw (145k+ GitHub stars), CrewAI, LangGraph all support OpenAI-compatible backends
- **Open concerns from v1.0:** Oracle feed creation (critical path), POL paired asset shortage, governance concentration risk, developer adoption targets
- **Deferred from v1.1:** IL modeling, tornado charts, competitive benchmarks, cross-model consistency checks

## Constraints

- **Tech stack (modeling)**: Python 3.x with openpyxl for Excel generation -- no external data dependencies
- **Tech stack (v1.2)**: Python (FastAPI + vLLM), Docker -- GPU inference infrastructure
- **Model serving**: vLLM v0.15.0+ with OpenAI-compatible API -- industry standard
- **Target hardware**: 4x H200 GPUs minimum for K2.5 production serving
- **API compatibility**: Must be OpenAI-compatible (drop-in for any existing integration)
- **Output format**: .xlsx files that work in Excel and Google Sheets (modeling)
- **Audience**: Non-technical leadership (strategy), developers (API/infrastructure)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python + openpyxl over Google Sheets API | No auth setup needed, generates portable .xlsx files | Good -- validated in v1.1 |
| Deterministic scenarios over Monte Carlo | Leadership needs clear scenario comparison, not probability distributions | Good -- validated in v1.1 |
| Master + standalone models | Master for integrated analysis, standalones for focused sharing | Good -- validated in v1.1 |
| param_refs dict as interface contract | All model builders receive cell addresses, no hardcoded values | Good -- scales to 70+ params |
| 70 params (vs ~50 estimated) | Include all research values without omission | Good -- more comprehensive |
| IL modeling deferred to v2 | Wrong IL estimate worse than none for concentrated liquidity | Pending -- still valid |
| Named ranges avoided | Industry anti-pattern; debugging complexity; openpyxl limitations | Good -- direct refs work well |
| openpyxl 3.1.5 with app.xml fix | Chart rendering bug workaround | Good -- no downgrade needed |

| Kimi K2.5 as flagship model | First-to-market on decentralized, native agentic + multimodal | Pending |
| Option C hybrid agent inference | Agent-aware extensions over standard API, not full agent hosting | Pending |
| vLLM over other serving frameworks | Industry standard, OpenAI-compatible, K2.5 officially supported | Pending |

---
*Last updated: 2026-02-13 after v1.2 milestone start*
