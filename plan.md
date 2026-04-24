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
  - ChromaDB as first pass vector store,
  - web retrieval fallback when internal evidence is insufficient using `ddgs` (DuckDuckGo Search).
- Proxy Layer:
  - `mattes/rotating-proxy` container for `ddgs` to facilitate high request rates. It uses HAProxy to load-balance requests across multiple Tor instances, providing a pool of rotating exit nodes.
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
   - Generate 5 highly targeted, SEO-optimized search queries per verifiable subclaim.
   - **SEO Strategies:** Prioritize keyword density (entities + metrics + dates) over natural language; utilize search operators (exact match quotes, `OR` logic); employ intent-based stratification (Official, News reporting, Debunking, Contextual).
3. Evidence Retrieval Agent
   - Query ChromaDB first.
   - **Web Fallback Pipeline:** If ChromaDB is insufficient, fetch the top 10 results for each of the 5 generated queries (max 50 URLs per claim).
   - **High-Volume Search:** Use `ddgs` routed through a Tor Proxy to maintain high throughput and avoid search engine rate limits.
   - **MBFC Pre-Flight Check:** Perform immediate domain lookup against MBFC SQLite; discard any URL from an unknown or untrusted domain before scraping.
   - **Contextual Passage Isolation:** Scrape full text from approved URLs using a lightweight parser (e.g., BeautifulSoup) to strip HTML, CSS, and extraneous DOM elements. Leverage a long-context LLM (e.g., Google's gemini-2.5-flash) to process the cleaned extracted text and isolate only the exact passages directly pertinent to the subclaim before passing them to the Ensemble Agent.
4. Credibility and Lineage Agent
   - Score source reliability using MBFC SQLite registry and track lineage metadata.
   - **Hard Reject Policy:** Canonicalize domains and reject evidence from sources that are:
    1. Missing from the MBFC registry.
    2. Ranked as `Low` or `Very Low` in factual reporting.
    This eliminates misinformation risk by ensuring only high-signal sources reach the Ensemble Agent.
5. Ensemble Decision Agent
   - **Strict Consensus Logic:** Performs pairwise comparison of high-credibility evidence.
   - If any two sources flatly contradict (mutually exclusive data), flags as `contradictory_evidence`.
   - **Weighted Fusion Logic:** If no hard contradictions are found, computes a final score by combining independent specialist signals:
     - *Source Reliability:* Based on MBFC "Factual Reporting" scores.
     - *Recency:* Decay-weighted based on publication date vs. claim context.
     - *Semantic Entailment:* LLM-scored alignment between evidence text and claim.
     - *Quantity:* Number of independent high-credibility domains providing supporting evidence.
   - **Fusion Calculation:** `Final Score = Σ (Signal_i * Weight_i)`. If the score is in the "gray zone" (e.g., 0.4 - 0.6), the agent defaults to `Uncertain (insufficient_evidence)`.
6. Verification and Report Agent
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
    2. *Recency* (Publication date vs. claim context).
    3. *Semantic Entailment* (LLM-scored alignment).
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
   - Chroma-miss -> Web fallback retrieves Source A (2%) and Source B (5%).

5. Credibility and Lineage Agent
   - Both Source A and B are in MBFC registry -> Accepted.

6. Ensemble Decision Agent (Strict Consensus)
   - Detects 2% vs 5% contradiction.
   - Flags `uncertainty_type = contradictory_evidence`.
   - Populates `conflict_details`.

7. Verification and Report Agent
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
4. Hybrid evidence retrieval (ChromaDB-first, web fallback).
5. Source credibility filtering (MBFC Hard Reject).
6. Ensemble verdict computation (Strict Consensus logic).
7. Final verification and report synthesis (Conflict explanations).
8. Deployment orchestration (Docker + Cloudflare).

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
- Deployment uses single-host Docker Compose and Cloudflare Tunnel.

## 10) Deployment Architecture
- `app`: Streamlit + Orchestrator.
- `chromadb`: Private vector store.
- `tor-proxy`: Tor-based HTTP proxy for rotating outgoing search IPs.
- `cloudflared`: Public ingress only to `app:8501`.
- Volumes for `chroma_data` and `mbfc_data`.

## 11) Recommended Project Structure
The project should follow a standard Python package layout to separate orchestration, data models, and agent logic:

```text
neutral-detection-agents-workflow/
├── .env.example                 # Template for API keys and config (OpenAI, Gemini, Tavily, etc.)
├── docker-compose.yml           # Runs app, chromadb, and cloudflared
├── Dockerfile                   # Builds the main Streamlit/LangChain app
├── pyproject.toml               # Python dependencies
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
    │   ├── web_search.py        # Web search API integration (e.g., Tavily/Google)
    │   └── web_scraper.py       # BeautifulSoup extraction logic
    │
    ├── agents/                  # Individual Agent Implementations
    │   ├── __init__.py
    │   ├── claim_decomposition.py
    │   ├── query_generation.py  # SEO-optimized query logic
    │   ├── evidence_retrieval.py# Chroma query + Web scrape + gemini-2.5-flash passage isolation
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
