# Agentic System for Information Neutrality and Turthfulness Detection

Implementation TODO list based on `plan.md`.

## 1) Project setup
- [x] Create project skeleton: `src/`, `tests/`, `scripts/`, `data/`.
- [x] Add dependency management (`pyproject.toml`).
- [x] Add env config template (`.env.example`) for API keys and runtime flags.
- [ ] Add basic logging and config loader (dev/prod modes).
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
- [ ] **ChromaDB Service (`src/services/chroma_store.py`)**: Initialize, vector search, `upsert_evidence`.
- [ ] **Redis Cache Service (`src/services/redis_cache.py`)**: Transient storage for scraped payloads.
- [ ] **Web Search Service (`src/services/web_search.py`)**: Integrate `ddgs` (DuckDuckGo Search) with `rotating-proxy` support.
- [ ] **Scraping Service (`src/services/web_scraper.py`)**: BeautifulSoup parser for clean text.
- [ ] **MBFC Pre-Flight Logic**: Integrate into retrieval to drop URLs before scraping.
- [ ] **Normalization & Write-back**: Map to `Evidence` model and perform "Verification Gate" check.

## 5) Agent implementations (`src/agents/`)
- [ ] Claim Decomposition Agent
- [ ] Query Generation Agent
- [ ] Evidence Retrieval Agent
- [ ] Passage Isolation Agent
- [ ] Credibility and Lineage Agent
- [ ] Ensemble Decision Agent
- [ ] Verification and Report Agent

## 6) Orchestration (`src/workflow/`)
- [ ] Implement `state.py` (LangGraph state) and `graph.py` (nodes/edges).
- [ ] Add quality gates: Citation, Contradiction, Confidence thresholds.
- [ ] Add workflow-level trace IDs.

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
- [ ] Configure `docker-compose.yml` (app, chromadb, redis, tor-proxy, cloudflared).
- [ ] Volume configuration for `chroma_data` and `mbfc_data`.

