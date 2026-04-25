# Agentic System for Information Neutrality and Turthfulness Detection

Implementation TODO list based on `plan.md`.

## 1) Project setup
- [x] Create project skeleton: `src/`, `tests/`, `scripts/`, `data/`.
- [x] Add dependency management (`pyproject.toml`).
- [x] Add env config template (`.env.example`) for API keys and runtime flags.
- [x] Add basic logging and config loader (dev/prod modes).
- [ ] Add Docker assets scaffold: `docker-compose.yml`, `Dockerfile`, `.dockerignore`.
- [x] Add `redis.conf` optimized for transient caching.

## 2) Core data contracts
- [x] Implement typed models for `Claim`, `Evidence`, `SourceProfile`, `AgentOutput`, and `VerdictReport`.
- [x] Add validation rules (required fields, enum values, score ranges).
- [x] Add serialization helpers for state passing between agents.

## 3) MBFC SQLite credibility registry
- [x] Create SQLite schema migration.
- [x] Build one-time import script to load MBFC JSON snapshot.
- [x] Add domain canonicalization utility.
- [x] Implement lookup service with MBFC hit/miss logic (Hard Reject Policy).
- [x] Add indexes for fast domain lookup.

## 4) Retrieval layer (ChromaDB, Redis & Web Fallback)
- [x] **ChromaDB Service (`src/services/chroma_store.py`)**: Initialize, vector search, `upsert_evidence`.
- [x] **Redis Cache Service (`src/services/redis_cache.py`)**: Transient storage for scraped payloads.
- [x] **Web Search Service (`src/services/web_search.py`)**: Integrate Tavily Search API for reliable, LLM-optimized web retrieval.
- [x] **Scraping Service (`src/services/web_scraper.py`)**: BeautifulSoup parser for clean text.
- [x] **MBFC Pre-Flight Logic**: Integrate into retrieval to drop URLs before scraping.
- [x] **Normalization & Write-back**: Map to `Evidence` model and perform "Verification Gate" check.

## 5) Agent implementations (`src/agents/`)
- [x] Claim Decomposition Agent
- [x] Query Generation Agent
- [x] Evidence Retrieval Agent
- [x] Passage Isolation Agent
- [x] Credibility and Lineage Agent
- [x] Ensemble Decision Agent
- [x] Verification and Report Agent

## 6) Orchestration (`src/workflow/`)
- [x] Implement `state.py` (LangGraph state) and `graph.py` (nodes/edges).
- [x] Add quality gates: Citation, Contradiction, Confidence thresholds.
- [x] Add workflow-level trace IDs.

## 7) Streamlit UI (`src/app.py`)
- [ ] Build input form, verdict table, confidence/rationale display.
- [ ] **Conflict View**: Side-by-side comparison.
- [ ] Debug panel (agent outputs + timing).

## 8) Testing
- [ ] Unit tests (agents, models, utils).
- [ ] Integration tests (contradiction path, rejection path, docker boot).

## 9) Observability and evaluation
- [ ] Track latency, uncertainty rates, and structured logs.

## 10) Deployment
- [ ] Configure `docker-compose.yml` (app, chromadb, redis, cloudflared).
- [ ] Volume configuration for `chroma_data` and `mbfc_data`.

