# Multi-Agent Fact-Checking System Plan (Ensemble-Heavy MVP)

## 1) Summary
Build an ensemble-heavy, centralized multi-agent system that:
- extracts factual claims from user input,
- retrieves and validates evidence using a hybrid strategy (ChromaDB first, web fallback),
- produces a verdict with confidence and citations,
- returns corrections or explainable uncertainty when evidence is weak or conflicting.
- runs all components in Docker Compose and exposes only the UI via Cloudflare Tunnel.

MVP priority is correctness and transparency first, with performance optimization in a later phase.

## 2) Problem Framing
### Primary Goal
Given an input message, identify verifiable claims, assess factuality using trusted evidence, and return:
- verdict (`Supported`, `Not Supported`, `Uncertain`),
- confidence score,
- concise rationale,
- citations and correction when applicable.
- **Explainable Uncertainty:** Detailed reasons for `Uncertain` verdicts (e.g., source conflict vs. missing evidence).

### Boundaries
- In scope:
  - claim decomposition,
  - evidence retrieval and credibility filtering,
  - citation-backed verdicts and corrections,
  - explicit uncertainty output with conflict transparency.
- Out of scope:
  - legal judgments,
  - censorship decisions,
  - unsupported subjective opinion generation.

### Non-Goals
- Producing claims or opinions without evidence.
- Replacing legal/policy adjudication processes.

## 3) System Design
### Core Stack (MVP)
- UI: Streamlit (with conflict-comparison views).
- Orchestration: LangGraph-style centralized state machine (implemented via LangChain ecosystem).
- Retrieval:
  - ChromaDB as first pass vector store.
  - **Embedding Model:** `BAAI/bge-small-en-v1.5` running on **CUDA** (if available) via `sentence-transformers`.
  - **Query Strategy:** Use BGE v1.5 specific retrieval instruction: `"Represent this sentence for searching relevant passages: "`.
  - web retrieval fallback when internal evidence is insufficient using `ddgs` (DuckDuckGo Search).
- Transient Storage (Redis):
  - **Purpose:** Pass large scraped text payloads between agents without bloating the LangGraph state.
  - **Setup:** A dedicated `redis` container in Docker Compose, configured via `redis.conf` for zero persistence and `allkeys-lru` eviction.
  - **Connection:** Managed via `REDIS_URL` in environment configuration.
  - **TTL Policy:** All keys are set with a strict 15-minute TTL to ensure the cache remains transient.
  - **Key Schema:** `scrape:{claim_id}:{url_hash}`.
- Search API:
  - Tavily Search API for reliable, LLM-optimized web retrieval.
- Source credibility registry:
  - SQLite database seeded from MBFC JSON snapshot,
  - contains bias classifications, factual reporting scores, and credibility assessments for 9,000+ sources.

### Coordination Model
Centralized orchestrator controls agent sequence, retries, quality gates, and final report assembly.

### Agents (MVP)
1. Claim Decomposition Agent
   - Split input into atomic subclaims.
   - Filter verifiable vs non-verifiable statements.
2. Query Generation Agent
   - Generate 2 highly targeted, SEO-optimized search queries per verifiable subclaim.
   - **SEO Strategies:** Prioritize keyword density (entities + metrics + dates) over natural language; utilize search operators (exact match quotes, `OR` logic); employ intent-based stratification (Official, News reporting, Debunking, Contextual).
3. Evidence Retrieval Agent
   - Query ChromaDB first.
   - **Web Fallback Pipeline:** If ChromaDB is insufficient, fetch the top 3 results for each of the 2 generated queries (max 6 URLs per claim).
   - **Tavily Search:** Use Tavily API to maintain high throughput and reliability, bypassing the need for complex proxy rotation.
   - **MBFC Pre-Flight Check:** Perform immediate domain lookup against MBFC SQLite; discard any URL from an unknown or untrusted domain before scraping.
   - **Transient Caching:** Scrape full text from approved URLs using a lightweight parser (e.g., BeautifulSoup) to strip HTML, CSS, and extraneous DOM elements. Store the raw text payload into Redis with a short TTL (e.g., 15 mins), and pass only the resulting Redis key to the LangGraph state.
4. Passage Isolation Agent
   - Read the raw scraped text from Redis using the key provided in the state.
   - Leverage a long-context LLM (e.g., Google's gemini-2.5-flash) to process the cleaned extracted text and isolate only the exact passages directly pertinent to the subclaim.
   - Output refined `Evidence` objects containing the isolated excerpt, effectively dropping the massive raw text payload.
5. Credibility and Lineage Agent
   - Score source reliability using MBFC SQLite registry and track lineage metadata.
   - **Hard Reject Policy:** Canonicalize domains and reject evidence from sources that are:
    1. Missing from the MBFC registry.
    2. Ranked as `Low` or `Very Low` in factual reporting.
    This eliminates misinformation risk by ensuring only high-signal sources reach the Ensemble Agent.
6. Ensemble Decision Agent
   - **Strict Consensus Logic:** Performs pairwise comparison of high-credibility evidence.
   - If any two sources flatly contradict (mutually exclusive data), flags as `contradictory_evidence`.
   - **Weighted Fusion Logic:** If no hard contradictions are found, computes a final score by combining independent specialist signals:
     - *Source Reliability:* Based on MBFC "Factual Reporting" scores.
     <!-- - *Recency:* Decay-weighted based on publication date vs. claim context. -->
     - *Semantic Entailment:* LLM-scored alignment between evidence text and claim.
     - *Quantity:* Number of independent high-credibility domains providing supporting evidence.
   - **Fusion Calculation:** `Final Score = Σ (Signal_i * Weight_i)`. If the score is in the "gray zone" (e.g., 0.4 - 0.6), the agent defaults to `Uncertain (insufficient_evidence)`.
7. Verification and Report Agent
   - Validates logical consistency and citation completeness.
   - **Explainable Uncertainty Logic:** If conflict detected, preserves conflicting IDs and generates a side-by-side rationale.
   - Produces user-facing verdict report.

## 4) Data Contracts and Interfaces
Define canonical objects across all agents using Pydantic V2 for validation:

- **`Claim`**
  - `id`: Unique UUID or hash.
  - `text`: Raw text (min 5 chars).
  - `type`: `ATOMIC` | `COMPOUND` | `NON_VERIFIABLE` (includes ambiguous/contextual).
  - `verifiable`: Boolean.
  - `timestamp_context`: Optional datetime context.

- **`Evidence`**
  - `source_url`: Validated HttpUrl.
  - `source_domain`: Canonicalized domain.
  - `source_type`: Default "news_article".
  - `published_at`: Optional datetime.
  - `credibility_score`: Float (0.0 - 1.0). Derived from:
    1. *Source Reliability* (MBFC score).
    <!-- 2. *Recency* (Publication date vs. claim context). -->
    2. *Semantic Entailment* (LLM-scored alignment).
  - `excerpt`: Isolated pertinent passage (min 10 chars).
  - `lineage`: Metadata dict (retrieval/isolation traces).

- **`SourceProfile`**
  - `domain`: Canonical domain.
  - `bias_classification`: MBFC bias rating.
  - `factual_reporting`: MBFC reporting score.
  - `credibility_assessment`: MBFC overall verdict.
  - `mbfc_last_updated_at`: Optional datetime.

- **`AgentOutput`**
  - `status`: `SUCCESS` | `ERROR` | `INSUFFICIENT_DATA` | `SKIPPED`.
  - `confidence`: Float (0.0 - 1.0).
  - `artifacts`: Dictionary of results.
  - `errors`: List of error messages.

- **`VerdictReport`**
  - `claim_id`: Reference to parent claim.
  - `verdict`: `Supported` | `Not Supported` | `Uncertain`.
  - `confidence`: Float (0.0 - 1.0).
  - `rationale`: Concise explanation.
  - `citations`: List of `Evidence` objects.
  - `uncertainty_type`: `insufficient_evidence` | `contradictory_evidence` | `none`.
  - `conflict_details`: Optional object with `primary_contradiction` and `conflicting_evidence_ids`.
  - `correction`: Optional corrected fact string.

- **`VectorRecordMetadata`**
  - `claim_id`, `source_url`, `source_domain`, `published_at`, `credibility_score`, `mbfc_decision`, `ingested_at`, `embedding_model_version`.

All agents must exchange structured outputs only.
Credibility lookups must use MBFC SQLite registry as the authoritative source filter.
ChromaDB stores only evidence that passed MBFC and verification gates.

## 5) Sample Data Flow (Single Input Example)
### Input Example
User input:
`"Country X reduced inflation to 2% in 2025."`

### Step-by-Step Flow
1. Ingestion
   - Orchestrator creates workflow state container.

2. Claim Decomposition Agent
   - `c1`: "Country X reduced inflation to 2% in 2025." (`verifiable=true`)

3. Query Generation Agent
   - `"Country X inflation rate 2025 statistics"`, etc.

4. Evidence Retrieval Agent (Hybrid)
   - Chroma-miss -> Web fallback retrieves Source A (2%) and Source B (5%). Scrapes text and stores in Redis with keys `scrape:A` and `scrape:B`.

5. Passage Isolation Agent
   - Fetches raw text from Redis for A and B. Extracts the exact sentences mentioning "2%" and "5%". Emits refined `Evidence` objects.

6. Credibility and Lineage Agent
   - Both Source A and B are in MBFC registry -> Accepted.

7. Ensemble Decision Agent (Strict Consensus)
   - Detects 2% vs 5% contradiction.
   - Flags `uncertainty_type = contradictory_evidence`.
   - Populates `conflict_details`.

8. Verification and Report Agent
   - Generates rationale: "High-credibility sources provided mutually exclusive data points."
   - Final report payload includes the comparison metadata.

### Flow Rules
- No citation -> force `Uncertain (insufficient_evidence)`.
- Low-confidence ensemble -> force `Uncertain`.
- **Strict Consensus:** Any high-credibility contradiction -> force `Uncertain (contradictory_evidence)`.
- Unknown MBFC domains -> Hard reject (evidence excluded).

## 6) Task Decomposition
1. Input ingestion and claim decomposition.
2. Verifiability filtering and claim typing.
3. Query generation per claim.
4. Hybrid evidence retrieval (ChromaDB-first, web fallback using `ddgs`) and Redis caching.
5. Contextual passage isolation (LLM extraction from Redis cache).
6. Source credibility filtering (MBFC Hard Reject).
7. Ensemble verdict computation (Strict Consensus logic).
8. Final verification and report synthesis (Conflict explanations).
9. Deployment orchestration (Docker + Cloudflare).

## 7) Success Criteria
### Quality
- Every non-uncertain verdict includes traceable citations.
- **Explainability:** 100% of conflicted cases show the specific citations causing the conflict.

### Reliability and Safety
- Hard reject policy effectively blocks unknown-domain misinformation.
- Verification gate catches missing citations or logic gaps.

## 8) Verification Plan
### Integration Tests
- **Contradiction Path:** Two high-credibility sources disagree -> `Uncertain (contradictory_evidence)` with metadata.
- **Missing Path:** No sources found -> `Uncertain (insufficient_evidence)`.
- **Unknown Rejection Path:** Web evidence from non-MBFC domain -> Evidence dropped.

## 9) Assumptions and Defaults
- MBFC SQLite is the source of truth for "High Credibility."
- Unknown domains are hard rejected to prioritize safety over recall.
- **Vector Store:** ChromaDB uses Cosine similarity with BGE-small-en-v1.5 embeddings.
- **Hardware:** System defaults to CUDA for embedding generation if a compatible GPU is detected.
- Deployment uses single-host Docker Compose and Cloudflare Tunnel.

## 10) Deployment Architecture
- `app`: Streamlit + Orchestrator.
- `chromadb`: Private vector store.
- `redis`: Transient key-value store for passing scraped HTML between agents.
- **Tavily API:** External search API for reliable web retrieval.
- **GPU Acceleration:** Requires NVIDIA Container Toolkit and `nvidia` driver reservation in Compose.
- `cloudflared`: Public ingress only to `app:8501`.
- Volumes for `chroma_data` and `mbfc_data`.

## 11) Project Structure
The project should follow a standard Python package layout to separate orchestration, data models, and agent logic:

```text
neutral-detection-agents-workflow/
├── .env.example                 # Template for API keys and config (OpenAI, Gemini, DDGS_PROXY, etc.)
├── redis.conf                   # Redis configuration for transient caching
├── docker-compose.yml           # Runs app, chromadb, redis, and cloudflared
├── Dockerfile                   # Builds the main Streamlit/LangChain app
├── pyproject.toml               # Python dependencies (needs 'redis' added)
├── README.md
├── plan.md
│
├── data/                        # Local data (git-ignored)
│   ├── mbfc_snapshot.json       # Raw MBFC JSON file (for import script)
│   └── mbfc.sqlite              # The generated MBFC credibility registry (mounted in Docker)
│
├── scripts/                     # Operational scripts
│   └── import_mbfc_data.py      # One-time script to parse JSON and populate SQLite
│
├── tests/                       # Pytest suite
│   ├── unit/                    # Unit tests for agents, models, and utils
│   └── integration/             # End-to-end tests for the LangGraph workflow
│
└── src/                         # Main application code
    ├── __init__.py
    ├── config.py                # Environment variable loader and logging setup
    │
    ├── models/                  # Core Data Contracts (Pydantic / TypedDict)
    │   ├── __init__.py
    │   ├── claim.py             # Claim model
    │   ├── evidence.py          # Evidence and SourceProfile models
    │   └── report.py            # VerdictReport and AgentOutput models
    │
    ├── services/                # External Service Integrations
    │   ├── __init__.py
    │   ├── mbfc_registry.py     # SQLite connection and domain lookup logic
    │   ├── chroma_store.py      # ChromaDB connection, upsert, and query logic
    │   ├── web_search.py        # Web search integration (Tavily API)
    │   ├── web_scraper.py       # BeautifulSoup extraction logic
    │   └── redis_cache.py       # Redis connection and transient caching logic
    │
    ├── agents/                  # Individual Agent Implementations
    │   ├── __init__.py
    │   ├── claim_decomposition.py
    │   ├── query_generation.py  # SEO-optimized query logic
    │   ├── evidence_retrieval.py# Chroma query + Web scrape + Redis caching
    │   ├── passage_isolation.py # Reads Redis + gemini-2.5-flash extraction
    │   ├── credibility.py       # MBFC Hard Reject scoring logic
    │   ├── ensemble_decision.py # Strict Consensus & Weighted Fusion logic
    │   └── verification.py      # Rationale generation and Explainable Uncertainty
    │
    ├── workflow/                # LangGraph Orchestration
    │   ├── __init__.py
    │   ├── state.py             # Defines the LangGraph state object
    │   └── graph.py             # Defines nodes, edges, and routing logic
    │
    ├── utils/                   # Shared helpers
    │   ├── __init__.py
    │   └── domain_parser.py     # Canonicalize domains (strip www, https, trailing slashes)
    │
    └── app.py                   # Streamlit UI entry point
```
