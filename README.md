# NeutralCheck MAS: Multi-Agent Fact-Checking System

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Framework](https://img.shields.io/badge/framework-LangGraph-orange.svg)](https://github.com/langchain-ai/langgraph)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Hosted Service](https://img.shields.io/badge/Demo-Multi--Agent%20Fact--Checking%20System-brightgreen)](https://fact-checker.tungo-dev.com/)

**NeutralCheck** is a high-precision, Multi-Agent System (MAS) designed to align narratives with factual reality. It decomposes complex text into atomic claims, retrieves evidence via a hybrid (ChromaDB + Web) strategy, and reaches consensus using an ensemble of specialized agents.

---

## 1. System Architecture

NeutralCheck is built as a stateful, cyclic graph using **LangGraph**. The system maintains a central `WorkflowState` that evolves as agents process claims.

### High-Level Data Flow
1. **Input Ingestion:** User provides a statement or paragraph.
2. **Decomposition:** Text is broken into verifiable atomic claims.
3. **Hybrid Retrieval:** ChromaDB is searched first; if insufficient, a Tavily-powered web search is triggered.
4. **Scraping & Isolation:** Raw web content is cached in **Redis** and refined by a long-context LLM (Gemini 2.0 Flash) to isolate specific pertinent passages.
5. **Credibility Filtering:** All evidence is strictly validated against a local **MBFC (Media Bias/Fact Check)** SQLite registry.
6. **Ensemble Decision:** Specialized logic performs "Strict Consensus" and "Weighted Fusion" to reach a verdict.

---

## 2. Agent Catalog

| Agent Name | Role / Persona | Key Tools | Primary Model |
| :--- | :--- | :--- | :--- |
| **Claim Decomposition** | Splits text into atomic, verifiable subclaims | Pydantic Parser | GPT-4o-mini |
| **Query Generation** | Generates SEO-optimized search queries | Search Strategy | GPT-4o-mini |
| **Evidence Retrieval** | Orchestrates hybrid search & caching | ChromaDB, Redis, Tavily | N/A (Service-based) |
| **Passage Isolation** | Extracts relevant blocks from raw text | BeautifulSoup, Redis | Gemini 2.0 Flash |
| **Credibility Agent** | Scores relevance and enforces MBFC policy | MBFC Registry | GPT-4o-mini |
| **Ensemble Decision** | Reaches consensus with conflict detection | Weighted Fusion Logic | Custom Logic |
| **Verification Agent** | Synthesizes final reports and citations | Synthesis Engine | GPT-4o-mini |

---

## 3. Workflow & Interaction

*   **Input:** A statement like *"Country X reduced inflation to 2% in 2025."*
*   **Process:**
    *   The **Decomposition Agent** identifies the verifiable claim.
    *   The **Retrieval Agent** fetches data. If Source A says "2%" and Source B says "5%", the **Ensemble Agent** detects the contradiction.
    *   Instead of a simple "False", the system flags it as `Uncertain (contradictory_evidence)`.
*   **Output:** A structured report including a Verdict (Supported/Not Supported/Uncertain), Confidence Score, Rationale, and specific Citations.

---

## 4. Getting Started

### Prerequisites
*   Python 3.11+
*   Docker & Docker Compose (for ChromaDB and Redis)
*   `uv` (recommended for dependency management)

### API Keys
Create a `.env` file based on `.env.example`:
```bash
OPENAI_API_KEY=your_key
GOOGLE_API_KEY=your_key
TAVILY_API_KEY=your_key
```

### Installation
```bash
git clone https://github.com/your-username/neutral-detection-agents-workflow.git
cd neutral-detection-agents-workflow
pip install uv
uv sync
```

### Running with Docker
```bash
docker-compose up -d
```

Now streamlit UI will be accessible at http://localhost:8501

---

## 5. Monitoring & Observability

NeutralCheck includes built-in observability features:
*   **Real-time Logs:** The Streamlit UI displays agent "thoughts" and workflow progress using a custom `WorkflowLogger`.
*   **Conflict View:** When contradictory evidence is found, the UI provides a side-by-side comparison of the conflicting sources.
*   **Trace IDs:** Every request is assigned a unique UUID to track execution across the MAS.

---

## 6. Evaluation & Performance

*   **Hard Reject Policy:** We prioritize safety over recall. Any evidence from a domain ranked "Low" or "Very Low" in factual reporting by MBFC is automatically dropped.
*   **Explainable Uncertainty:** Verdicts are not just labels; they explain *why* evidence was insufficient or contradictory.

---

## 7. License & Acknowledgments
*   **License:** MIT
*   **Frameworks:** Built with [LangGraph](https://github.com/langchain-ai/langgraph) and [LangChain](https://github.com/langchain-ai/langchain).
*   **Data:** Credibility data provided by [Media Bias/Fact Check](https://mediabiasfactcheck.com/).
