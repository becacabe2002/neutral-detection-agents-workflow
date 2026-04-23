
# Multi-Agent Fact-Checking System Plan (Ensemble-Heavy MVP)

## 1) Summary
Build an ensemble-heavy, centralized multi-agent system that:
- extracts factual claims from user input,
- retrieves and validates evidence using a hybrid strategy (ChromaDB first, web fallback),
- produces a verdict with confidence and citations,
- returns corrections or uncertainty when evidence is weak.
- runs all components in Docker Compose and exposes only the UI via Cloudflare Tunnel.

MVP priority is correctness and transparency first, with performance optimization in a later phase.

## 2) Problem Framing
### Primary Goal
Given an input message, identify verifiable claims, assess factuality using trusted evidence, and return:
- verdict (`Supported`, `Not Supported`, `Uncertain`),
- confidence score,
- concise rationale,
- citations and correction when applicable.

### Boundaries
- In scope:
  - claim decomposition,
  - evidence retrieval and credibility filtering,
  - citation-backed verdicts and corrections,
  - explicit uncertainty output when evidence is insufficient.
- Out of scope:
  - legal judgments,
  - censorship decisions,
  - unsupported subjective opinion generation.

### Non-Goals
- Producing claims or opinions without evidence.
- Replacing legal/policy adjudication processes.

## 3) System Design
### Core Stack (MVP)
- UI: Streamlit.
- Orchestration: LangGraph-style centralized state machine (implemented via LangChain ecosystem).
- Retrieval:
  - ChromaDB as first pass vector store,
  - web retrieval fallback when internal evidence is insufficient.
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
   - Generate 3-4 high-intent search queries per verifiable subclaim.
3. Evidence Retrieval Agent
   - Query ChromaDB first.
   - Trigger web retrieval fallback only if ChromaDB evidence is insufficient.
4. Credibility and Lineage Agent
   - Score source reliability using MBFC SQLite registry and track lineage metadata (origin, date, source type).
   - Canonicalize domains and reject evidence from sources missing in MBFC registry (MVP policy: hard reject unknown domains).
5. Ensemble Decision Agent
   - Combine multiple specialist signals via weighted fusion for claim-level verdicts.
6. Verification and Report Agent
   - Validate logical consistency, citation completeness, and hallucination risk.
   - Produce user-facing verdict report.

## 4) Data Contracts and Interfaces
Define canonical objects across all agents:
- `Claim`
  - `id`, `text`, `type`, `verifiable`, `timestamp_context`
- `Evidence`
  - `source_url`, `source_domain`, `source_type`, `published_at`, `credibility_score`, `excerpt`, `lineage`
- `SourceProfile`
  - `domain`, `bias_classification`, `factual_reporting`, `credibility_assessment`, `mbfc_last_updated_at`
- `AgentOutput`
  - `status`, `confidence`, `artifacts`, `errors`
- `VerdictReport`
  - `claim_id`, `verdict`, `confidence`, `rationale`, `citations`, `uncertainty_note`, `correction`
- `VectorRecordMetadata`
  - `claim_id`, `source_url`, `source_domain`, `published_at`, `credibility_score`, `mbfc_decision`, `ingested_at`, `embedding_model_version`

All agents must exchange structured outputs only, not free-form text blobs.
Credibility lookups must use MBFC SQLite registry as the authoritative source filter in MVP.
ChromaDB stores only evidence that passed MBFC and verification gates.

## 5) Sample Data Flow (Single Input Example)
### Input Example
User input:
`"Country X reduced inflation to 2% in 2025 and unemployment fell to 3%."`

### Step-by-Step Flow
1. Ingestion
   - Orchestrator receives raw text plus request metadata (`request_id`, `received_at`, locale).
   - Creates workflow state container for all downstream agent outputs.

2. Claim Decomposition Agent
   - Splits into atomic claims:
     - `c1`: "Country X reduced inflation to 2% in 2025."
     - `c2`: "Country X unemployment fell to 3%."
   - Marks both as `verifiable=true`.
   - Output shape:
     ```json
     {
       "status": "ok",
       "confidence": 0.91,
       "artifacts": {
         "claims": [
           {"id":"c1","text":"...","type":"economic_stat","verifiable":true,"timestamp_context":"2025"},
           {"id":"c2","text":"...","type":"economic_stat","verifiable":true,"timestamp_context":"2025"}
         ]
       },
       "errors": []
     }
     ```

3. Query Generation Agent
   - Produces 3-4 queries per claim with date-aware phrasing.
   - Example for `c1`:
     - `"Country X inflation rate 2025 official statistics"`
     - `"Country X CPI annual average 2025 central bank"`
     - `"Country X inflation 2 percent 2025 report"`

4. Evidence Retrieval Agent (Hybrid)
   - First attempts ChromaDB retrieval for each claim.
   - If relevance/coverage threshold is not met, triggers web fallback.
   - Normalizes and stages newly retrieved web evidence for ingestion.
   - Branching:
     - Chroma-hit: proceed with internal evidence only.
     - Chroma-miss or weak evidence: append web evidence and mark retrieval path as `hybrid`.
   - After verification approval, persist newly accepted evidence chunks into ChromaDB with metadata (`claim_id`, `source_url`, `source_domain`, `published_at`, `credibility_score`, `mbfc_decision`, `ingested_at`, `embedding_model_version`) to improve future recall.

5. Credibility and Lineage Agent
   - Canonicalizes each evidence URL to domain and looks up MBFC SQLite profile.
   - Scoring branch:
     - MBFC profile found: compute source reliability using MBFC factual reporting + credibility fields.
     - MBFC profile missing: hard reject evidence (`mbfc_decision = rejected_unknown`).
   - Scores each remaining evidence item (source reliability, recency, domain trust).
   - Attaches lineage:
     - source origin,
     - publication timestamp,
     - extraction method,
     - claim-to-evidence mapping score,
     - MBFC profile fields used in scoring.
   - Drops evidence below minimum credibility threshold.

6. Ensemble Decision Agent
   - Runs specialist evaluators (for example: numeric consistency, semantic entailment, source agreement).
   - Produces weighted fusion score per claim.
   - Example outcome:
     - `c1`: `Supported`, confidence `0.86`
     - `c2`: `Uncertain`, confidence `0.54` (insufficient high-credibility evidence)

7. Verification and Report Agent
   - Validates that each non-uncertain verdict has citations.
   - Checks rationale-evidence consistency and flags contradictions.
   - Generates final report payload:
     ```json
     {
       "request_id": "req_123",
       "results": [
         {
           "claim_id": "c1",
           "verdict": "Supported",
           "confidence": 0.86,
           "rationale": "Official CPI publication aligns with 2% figure.",
           "citations": ["https://example.gov/statistics/cpi-2025"],
           "uncertainty_note": null,
           "correction": null
         },
         {
           "claim_id": "c2",
           "verdict": "Uncertain",
           "confidence": 0.54,
           "rationale": "Conflicting unemployment estimates across sources.",
           "citations": ["https://example.org/labor-data-2025"],
           "uncertainty_note": "Insufficient consensus from high-credibility evidence.",
           "correction": "Latest verified unemployment range is 3.6%-4.1%."
         }
       ]
     }
     ```

### Flow Rules
- No citation -> cannot emit `Supported` or `Not Supported`; force `Uncertain`.
- Low-confidence ensemble output -> require verification gate downgrade to `Uncertain`.
- Missing DB evidence does not fail request; web fallback is mandatory before final uncertainty.
- Newly retrieved web evidence is only added to ChromaDB after credibility and verification gates pass.
- Evidence from domains not present in MBFC SQLite is excluded from decision stage (hard reject).

## 6) Task Decomposition
1. Input ingestion and claim decomposition.
2. Verifiability filtering and claim typing.
3. Query generation per claim.
4. Hybrid evidence retrieval (ChromaDB-first, web fallback).
5. Source credibility filtering and lineage attachment.
   - Includes MBFC SQLite domain lookup and unknown-source rejection.
6. Ensemble verdict computation.
7. Final verification and report synthesis.
8. Deployment orchestration with Docker Compose and Cloudflare Tunnel ingress.

## 7) Success Criteria
### Quality
- End-to-end system correctly flags at least 80% of claims on evaluation suite.
- Every non-uncertain verdict includes traceable citations.
- Uncertain cases explicitly state evidence insufficiency.

### Reliability and Safety
- Verification gate catches missing citations, weak confidence, and contradictory rationale.
- High-risk outputs fall back to `Uncertain` instead of overconfident assertions.

### Performance (MVP)
- No strict hard latency SLA in MVP.
- Track p50/p95 latency from day one and optimize after baseline quality is stable.

## 8) Verification Plan
### Unit Tests
- Claim decomposition and verifiability filtering.
- Query generation constraints (quality and non-duplication).
- Credibility scoring behavior for trusted/untrusted/unknown domains.
- Domain canonicalization and MBFC SQLite lookup hit/miss behavior.

### Integration Tests
- Chroma-hit path (no web fallback).
- Chroma-miss path (web fallback active).
- Ensemble disagreement path leading to low-confidence/uncertain outcome.
- Unknown-domain evidence path -> evidence rejected before ensemble scoring.
- Verified accepted evidence path -> ChromaDB write-back only after MBFC + verification pass.
- Docker Compose startup path -> app, ChromaDB, and cloudflared healthy.
- External access path -> Cloudflare hostname routes to Streamlit only; ChromaDB is not public.

### Acceptance Scenarios
- Clearly true claim with strong evidence.
- False claim with conflicting sources.
- Ambiguous claim with insufficient evidence and explicit uncertainty.
- Time-sensitive claim with stale evidence down-weighted.

## 9) Assumptions and Defaults
- Centralized orchestration is the MVP default.
- Ensemble can start with LLM-specialist agents before adding heavier model families.
- Hybrid retrieval policy is mandatory (`ChromaDB -> web fallback`).
- MBFC SQLite registry is seeded once in MVP via migration + JSON import script.
- Unknown domains are hard rejected in MVP.
- Performance tuning is phase 2; MVP ships after quality and traceability gates pass.
- Deployment uses single-host Docker Compose in MVP.
- Cloudflare Tunnel uses named tunnel token mode and exposes Streamlit publicly.

## 10) Deployment Architecture (Docker Compose + Cloudflare Tunnel)
### Services
- `app`: Streamlit UI, orchestrator, and all agent logic.
- `chromadb`: vector storage service for embeddings and filtered evidence metadata.
- `cloudflared`: outbound tunnel client routing Cloudflare edge traffic to `app:8501`.

### Network and Exposure
- Internal Docker network (`factcheck_net`) for service-to-service traffic.
- Do not expose `chromadb` to the public internet.
- Public ingress is only through Cloudflare Tunnel to Streamlit (`app:8501`).

### Persistence
- `chroma_data` named volume for ChromaDB persistence.
- `mbfc_data` volume or bind mount for MBFC SQLite file and import artifacts.

### Runtime Configuration
- Required env keys:
  - `TUNNEL_TOKEN`
  - `CF_TUNNEL_HOSTNAME`
  - `CHROMA_URL`
  - `MBFC_SQLITE_PATH`
- Optional app keys:
  - retrieval and LLM provider API keys.

### Operational Rules
- `app` waits for ChromaDB health before serving requests.
- `cloudflared` starts after `app` healthcheck passes.
- If tunnel is down, local stack remains usable on internal network.
