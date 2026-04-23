# Neutral Detection Agents Workflow

Implementation TODO list based on `plan.md`.

## 1) Project setup
- [ ] Create project skeleton: `src/`, `tests/`, `scripts/`, `data/`, `db/`.
- [ ] Add dependency management (`pyproject.toml` or `requirements.txt`).
- [ ] Add env config template (`.env.example`) for API keys and runtime flags.
- [ ] Add basic logging and config loader (dev/prod modes).
- [ ] Add Docker assets scaffold: `docker-compose.yml`, `Dockerfile`, `.dockerignore`.

## 2) Core data contracts
- [ ] Implement typed models for:
  - [ ] `Claim`
  - [ ] `Evidence`
  - [ ] `SourceProfile`
  - [ ] `AgentOutput`
  - [ ] `VerdictReport`
- [ ] Add validation rules (required fields, enum values, score ranges).
- [ ] Add serialization helpers for state passing between agents.

## 3) MBFC SQLite credibility registry
- [ ] Create SQLite schema migration for MBFC source registry.
- [ ] Build one-time import script to load MBFC JSON snapshot.
- [ ] Add domain canonicalization utility (`https`, `www`, subdomains, trailing dots).
- [ ] Implement lookup service:
  - [ ] MBFC hit -> return normalized `SourceProfile`
  - [ ] MBFC miss -> return `rejected_unknown` (hard reject policy)
- [ ] Add indexes for fast domain lookup.

## 4) Retrieval layer (ChromaDB)
- [ ] Implement ChromaDB interface (query + upsert + metadata filters).
- [ ] Implement web retrieval fallback pipeline.
- [ ] Add retrieval threshold logic (Chroma-hit vs Chroma-miss/weak evidence).
- [ ] Normalize retrieved evidence to canonical `Evidence` objects.
- [ ] Enforce write-back rule: upsert to ChromaDB only after credibility + verification pass.

## 5) Agent implementations
- [ ] Claim Decomposition Agent (atomic claims + verifiability filter).
- [ ] Query Generation Agent (3-4 targeted queries per claim).
- [ ] Evidence Retrieval Agent (DB-first + web fallback).
- [ ] Credibility and Lineage Agent (MBFC scoring + lineage metadata).
- [ ] Ensemble Decision Agent (weighted fusion over specialist signals).
- [ ] Verification and Report Agent (citation/rationale consistency + final report).

## 6) Orchestration
- [ ] Implement centralized orchestrator (LangGraph/LangChain state flow).
- [ ] Define stage transitions, retries, and failure handling.
- [ ] Add quality gates:
  - [ ] No citation => force `Uncertain`
  - [ ] Low confidence => downgrade to `Uncertain`
  - [ ] Unknown MBFC source => evidence excluded
- [ ] Add workflow-level trace IDs for debugging.

## 7) Streamlit UI
- [ ] Build input form for raw claim/message.
- [ ] Show claim-level verdict table (`Supported`, `Not Supported`, `Uncertain`).
- [ ] Display confidence, rationale, and citations per claim.
- [ ] Show uncertainty notes and corrections where applicable.
- [ ] Add simple debug panel (agent outputs + timing).

## 8) Testing
- [ ] Unit tests:
  - [ ] claim decomposition + verifiability
  - [ ] query generation constraints
  - [ ] domain canonicalization + MBFC lookup hit/miss
  - [ ] credibility scoring behavior
- [ ] Integration tests:
  - [ ] Chroma-hit path
  - [ ] Chroma-miss path with web fallback
  - [ ] unknown-domain rejection path
  - [ ] ensemble disagreement => `Uncertain`
  - [ ] verified evidence write-back path (ChromaDB)
  - [ ] docker compose boot path (`app`, `chromadb`, `cloudflared`)
  - [ ] tunnel routing path (public hostname -> Streamlit only)
- [ ] Acceptance scenarios from `plan.md` (true/false/ambiguous/time-sensitive claims).

## 9) Observability and evaluation
- [ ] Track p50/p95 latency per stage and end-to-end.
- [ ] Track quality metrics: claim accuracy, citation coverage, uncertainty rate.
- [ ] Add structured logs for decision path (why evidence accepted/rejected).
- [ ] Create a small evaluation runner for regression checks.

## 10) Release readiness
- [ ] Document local run steps and test commands.
- [ ] Add CI checks for tests and linting.
- [ ] Freeze MVP scope and open backlog for phase 2 improvements.

## 11) Deployment (Docker Compose + Cloudflare Tunnel)
- [ ] Build `app` container image (Streamlit + orchestrator + agents).
- [ ] Add `chromadb` service with persistent `chroma_data` volume.
- [ ] Add `cloudflared` service using named tunnel token (`TUNNEL_TOKEN`).
- [ ] Configure internal network and keep ChromaDB private.
- [ ] Route Cloudflare hostname to `http://app:8501`.
- [ ] Add healthchecks and startup dependencies (`app` waits for ChromaDB; `cloudflared` waits for `app`).
- [ ] Document deployment env vars:
  - [ ] `TUNNEL_TOKEN`
  - [ ] `CF_TUNNEL_HOSTNAME`
  - [ ] `CHROMA_URL`
  - [ ] `MBFC_SQLITE_PATH`
