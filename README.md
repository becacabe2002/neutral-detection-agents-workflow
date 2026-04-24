# Neutral Detection Agents Workflow

Implementation TODO list based on `plan.md`.

## 1) Project setup
- [x] Create project skeleton: `src/`, `tests/`, `scripts/`, `data/`.
- [x] Add dependency management (`pyproject.toml` or `requirements.txt`).
- [x] Add env config template (`.env.example`) for API keys and runtime flags.
- [ ] Add basic logging and config loader (dev/prod modes).
- [ ] Add Docker assets scaffold: `docker-compose.yml`, `Dockerfile`, `.dockerignore`.

## 2) Core data contracts
- [x] Implement typed models for:
  - [x] `Claim`
  - [x] `Evidence`
  - [x] `SourceProfile`
  - [x] `AgentOutput`
  - [x] `VerdictReport` (including `uncertainty_type` and `conflict_details`)
- [x] Add validation rules (required fields, enum values, score ranges).
- [x] Add serialization helpers for state passing between agents.

## 3) MBFC SQLite credibility registry
- [x] Create SQLite schema migration for MBFC source registry.
- [x] Build one-time import script to load MBFC JSON snapshot.
- [x] Add domain canonicalization utility.
- [x] Implement lookup service:
  - [x] MBFC hit -> return normalized `SourceProfile`
  - [x] MBFC miss -> return `rejected_unknown` (Hard Reject Policy)
- [x] Add indexes for fast domain lookup.

## 4) Retrieval layer (ChromaDB)
- [ ] Implement ChromaDB interface (query + upsert + metadata filters).
- [ ] Implement web retrieval fallback pipeline.
- [ ] Add retrieval threshold logic.
- [ ] Normalize retrieved evidence to canonical `Evidence` objects.
- [ ] Enforce write-back rule: upsert to ChromaDB only after credibility + verification pass.

## 5) Agent implementations
- [ ] Claim Decomposition Agent (atomic claims + verifiability filter).
- [ ] Query Generation Agent (5 SEO-optimized targeted queries per claim).
- [ ] Evidence Retrieval Agent (DB-first + web fallback, top 10 results, Contextual Passage Isolation using Gemini 2.5 Flash Lite).
- [ ] Credibility and Lineage Agent (MBFC Hard Reject scoring).
- [ ] Ensemble Decision Agent (Strict Consensus: pairwise contradiction check).
- [ ] Verification and Report Agent (Logic/citation consistency + explainable uncertainty generation).

## 6) Orchestration
- [ ] Implement centralized orchestrator (LangGraph/LangChain state flow).
- [ ] Define stage transitions, retries, and failure handling.
- [ ] Add quality gates:
  - [ ] No citation => force `Uncertain (insufficient_evidence)`
  - [ ] Contradiction => force `Uncertain (contradictory_evidence)`
  - [ ] Low confidence => downgrade to `Uncertain`
- [ ] Add workflow-level trace IDs for debugging.

## 7) Streamlit UI
- [ ] Build input form for raw claim/message.
- [ ] Show claim-level verdict table (`Supported`, `Not Supported`, `Uncertain`).
- [ ] Display confidence, rationale, and citations per claim.
- [ ] **Conflict View:** Side-by-side comparison for `contradictory_evidence`.
- [ ] Add simple debug panel (agent outputs + timing).

## 8) Testing
- [ ] Unit tests:
  - [ ] claim decomposition + verifiability
  - [ ] domain canonicalization + MBFC lookup
  - [ ] strict consensus contradiction detection
- [ ] Integration tests:
  - [ ] contradiction path -> `Uncertain (contradictory_evidence)`
  - [ ] unknown-domain rejection path
  - [ ] verified evidence write-back path
  - [ ] docker compose boot path
- [ ] Acceptance scenarios from `plan.md` (true/false/ambiguous/conflicting).

## 9) Observability and evaluation
- [ ] Track p50/p95 latency per stage and end-to-end.
- [ ] Track quality metrics: uncertainty rate (conflict vs. missing), accuracy.
- [ ] Add structured logs for decision path.

## 10) Release readiness
- [ ] Document local run steps and test commands.
- [ ] Add CI checks for tests and linting.

## 11) Deployment (Docker Compose + Cloudflare Tunnel)
- [ ] Build `app` container image.
- [ ] Add `chromadb` service with persistent volume.
- [ ] Add `rotating-proxy` service (using `mattes/rotating-proxy`) for search IP rotation (enables high request rate).
- [ ] Add `cloudflared` service using named tunnel token.
- [ ] Configure internal network (keep ChromaDB private).
- [ ] Route Cloudflare hostname to `http://app:8501`.
