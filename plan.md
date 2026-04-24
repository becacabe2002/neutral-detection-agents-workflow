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
   - Generate 5 highly targeted, SEO-optimized search queries per verifiable subclaim.
   - **SEO Strategies:** Prioritize keyword density (entities + metrics + dates) over natural language; utilize search operators (exact match quotes, `OR` logic); employ intent-based stratification (Official, News reporting, Debunking, Contextual).
3. Evidence Retrieval Agent
   - Query ChromaDB first.
   - **Web Fallback Pipeline:** If ChromaDB is insufficient, fetch the top 10 results for each of the 5 generated queries (max 50 URLs per claim).
   - **MBFC Pre-Flight Check:** Perform immediate domain lookup against MBFC SQLite; discard any URL from an unknown or untrusted domain before scraping.
   - **Contextual Passage Isolation:** Scrape full text from approved URLs using a lightweight parser (e.g., BeautifulSoup) to strip HTML, CSS, and extraneous DOM elements. Leverage a long-context LLM (e.g., Google's Gemini 2.5 Flash Lite) to process the cleaned extracted text and isolate only the exact passages directly pertinent to the subclaim before passing them to the Ensemble Agent.
4. Credibility and Lineage Agent
   - Score source reliability using MBFC SQLite registry and track lineage metadata.
   - **Hard Reject Policy:** Canonicalize domains and reject evidence from sources missing in MBFC registry to eliminate misinformation risk.
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
  - `claim_id`, `verdict`, `confidence`, `rationale`, `citations`, `uncertainty_type` (`insufficient_evidence` | `contradictory_evidence`), `conflict_details` (object with `primary_contradiction` and `conflicting_evidence_ids`), `correction`
- `VectorRecordMetadata`
  - `claim_id`, `source_url`, `source_domain`, `published_at`, `credibility_score`, `mbfc_decision`, `ingested_at`, `embedding_model_version`

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
- `cloudflared`: Public ingress only to `app:8501`.
- Volumes for `chroma_data` and `mbfc_data`.
