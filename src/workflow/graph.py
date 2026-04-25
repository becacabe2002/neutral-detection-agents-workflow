import asyncio
from typing import List
from langgraph.graph import StateGraph, END
from .state import WorkflowState
from src.agents.claim_decomposition import ClaimDecompositionAgent
from src.agents.query_generation import QueryGenerationAgent
from src.agents.evidence_retrieval import EvidenceRetrievalAgent
from src.agents.passage_isolation import PassageIsolationAgent
from src.agents.credibility import CredibilityAgent
from src.agents.ensemble_decision import EnsembleDecisionAgent
from src.agents.verification import VerificationAgent
from src.services.chroma_store import ChromaStore

async def decompose_claims_node(state: WorkflowState):
    """Decompose input text into atomic claims."""
    agent = ClaimDecompositionAgent()
    claims = await agent.run(state["input_text"])
    return {"claims": claims}

async def generate_queries_node(state: WorkflowState):
    """Generate search queries for each verifiable claim."""
    agent = QueryGenerationAgent()
    queries_map = {}
    verifiable_claims = [c for c in state["claims"] if c.verifiable]
    
    if verifiable_claims:
        results = await asyncio.gather(*[agent.run(c.text) for c in verifiable_claims])
        queries_map = {c.id: q for c, q in zip(verifiable_claims, results)}
        
    return {"queries": queries_map}

async def retrieve_evidence_node(state: WorkflowState):
    """Retrieve evidence (ChromaDB first, then web fallback)."""
    agent = EvidenceRetrievalAgent()
    evidence_keys_map = {}
    cached_evidences_map = {}
    
    claims_to_search = [c for c in state["claims"] if state.get("queries", {}).get(c.id)]
    
    if claims_to_search:
        results = await asyncio.gather(*[agent.run(c.id, state["queries"][c.id], c.text) for c in claims_to_search])
        for claim, (artifacts, cached) in zip(claims_to_search, results):
            if cached:
                cached_evidences_map[claim.id] = cached
            if artifacts:
                evidence_keys_map[claim.id] = artifacts
        
    return {"raw_evidence_keys": evidence_keys_map, "evidences": cached_evidences_map}

async def isolate_passages_node(state: WorkflowState):
    """Isolate passages from raw web content."""
    agent = PassageIsolationAgent()
    isolated_evidences_map = {}
    claims_to_process = [c for c in state["claims"] if c.id in state.get("raw_evidence_keys", {})]
    
    if claims_to_process:
        results = await asyncio.gather(*[agent.run(c, state["raw_evidence_keys"][c.id]) for c in claims_to_process])
        isolated_evidences_map = {c.id: evs for c, evs in zip(claims_to_process, results)}
        
    return {"evidences": isolated_evidences_map}

async def score_credibility_node(state: WorkflowState):
    """Score credibility of new isolated passages."""
    agent = CredibilityAgent()
    updated_evidences_map = {}
    tasks = []
    claims_with_new_evidence = []
    
    for claim in state["claims"]:
        evs = state.get("evidences", {}).get(claim.id, [])
        if not evs: continue
            
        new_ev = [e for e in evs if e.lineage.get("source") != "chromadb"]
        cached_ev = [e for e in evs if e.lineage.get("source") == "chromadb"]
        
        if new_ev:
            claims_with_new_evidence.append((claim, cached_ev))
            tasks.append(agent.run(claim, new_ev))
        else:
            updated_evidences_map[claim.id] = cached_ev
            
    if tasks:
        results = await asyncio.gather(*tasks)
        for (claim, cached), newly_scored in zip(claims_with_new_evidence, results):
            updated_evidences_map[claim.id] = cached + newly_scored
            
    return {"evidences": updated_evidences_map}

async def persist_evidence_node(state: WorkflowState):
    """Persist new high-quality evidence back to ChromaDB."""
    store = ChromaStore()
    for claim_id, evidences in state.get("evidences", {}).items():
        for ev in evidences:
            if ev.lineage.get("source") != "chromadb" and ev.credibility_score >= 0.7:
                store.upsert_evidence(claim_id, ev)
    return state

async def ensemble_decision_node(state: WorkflowState):
    """Reach ensemble verdicts."""
    agent = EnsembleDecisionAgent()
    tasks = [agent.run(c, state.get("evidences", {}).get(c.id, [])) for c in state["claims"]]
    results = await asyncio.gather(*tasks)
    return {"verdicts": {c.id: r for c, r in zip(state["claims"], results)}}

async def synthesize_report_node(state: WorkflowState):
    """Synthesize final reports and summary."""
    agent = VerificationAgent()
    claims_to_verify = [c for c in state["claims"] if c.id in state.get("verdicts", {})]
    
    if not claims_to_verify:
        return {"final_output": "No claims were identified for verification."}

    results = await asyncio.gather(*[agent.run(c, state["verdicts"][c.id]) for c in claims_to_verify])
    final_verdicts_map = {c.id: r for c, r in zip(claims_to_verify, results)}
        
    summary_parts = ["### Multi-Agent Fact-Checking Report\n"]
    for claim in state["claims"]:
        report = final_verdicts_map.get(claim.id)
        if report:
            verdict_label = report.verdict.value.upper()
            summary_parts.append(f"**[{verdict_label}] Claim:** {claim.text}")
            summary_parts.append(f"**Verdict:** {verdict_label} (Confidence: {report.confidence})")
            summary_parts.append(f"**Rationale:** {report.rationale}")
            if report.correction:
                summary_parts.append(f"**Correction:** {report.correction}")
            summary_parts.append("\n---\n")
    
    return {"verdicts": final_verdicts_map, "final_output": "\n".join(summary_parts)}

def create_workflow():
    workflow = StateGraph(WorkflowState)
    nodes = [
        ("decompose", decompose_claims_node),
        ("generate_queries", generate_queries_node),
        ("retrieve", retrieve_evidence_node),
        ("isolate", isolate_passages_node),
        ("score", score_credibility_node),
        ("persist", persist_evidence_node),
        ("ensemble", ensemble_decision_node),
        ("synthesize", synthesize_report_node)
    ]
    for name, func in nodes:
        workflow.add_node(name, func)

    workflow.set_entry_point("decompose")
    workflow.add_edge("decompose", "generate_queries")
    workflow.add_edge("generate_queries", "retrieve")
    workflow.add_edge("retrieve", "isolate")
    workflow.add_edge("isolate", "score")
    workflow.add_edge("score", "persist")
    workflow.add_edge("persist", "ensemble")
    workflow.add_edge("ensemble", "synthesize")
    workflow.add_edge("synthesize", END)

    return workflow.compile()

app_workflow = create_workflow()
