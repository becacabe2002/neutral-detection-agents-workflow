import asyncio
import uuid
from typing import List
from langgraph.graph import StateGraph, END
from .state import WorkflowState
from src.agents import (
    ClaimDecompositionAgent,
    QueryGenerationAgent,
    EvidenceRetrievalAgent,
    PassageIsolationAgent,
    CredibilityAgent,
    EnsembleDecisionAgent,
    VerificationAgent
)
from src.services import ChromaStore
from src.utils.logger import WorkflowLogger

async def decompose_claims_node(state: WorkflowState):
    """Decompose input text into atomic claims."""
    logger = WorkflowLogger.get_logger("decompose_node", state.get("trace_id", "N/A"))
    logger.info("Starting claim decomposition")
    agent = ClaimDecompositionAgent()
    claims = await agent.run(state["input_text"])
    logger.info(f"Decomposed into {len(claims)} atomic claims")
    return {
        "claims": claims, 
        "logs": [f"🧠 Decomposed input into {len(claims)} atomic claims."]
    }

async def generate_queries_node(state: WorkflowState):
    """Generate search queries for each verifiable claim."""
    logger = WorkflowLogger.get_logger("query_gen_node", state.get("trace_id", "N/A"))
    logger.info("Generating search queries for verifiable claims")
    agent = QueryGenerationAgent()
    queries_map = {}
    verifiable_claims = [c for c in state["claims"] if c.verifiable]
    
    if verifiable_claims:
        logger.info(f"Found {len(verifiable_claims)} verifiable claims")
        results = await asyncio.gather(*[agent.run(c.text, c.timestamp_context) for c in verifiable_claims])
        queries_map = {c.id: q for c, q in zip(verifiable_claims, results)}
        log_msg = f"🔍 Generated SEO queries for {len(verifiable_claims)} verifiable claims."
    else:
        logger.info("No verifiable claims found")
        log_msg = "ℹ️ No verifiable claims found; skipping query generation."
        
    return {"queries": queries_map, "logs": [log_msg]}

async def retrieve_evidence_node(state: WorkflowState):
    """Retrieve evidence (ChromaDB first, then web fallback)."""
    logger = WorkflowLogger.get_logger("retrieve_node", state.get("trace_id", "N/A"))
    logger.info("Retrieving evidence from ChromaDB and Web")
    agent = EvidenceRetrievalAgent()
    evidence_keys_map = {}
    cached_evidences_map = {}
    excluded_map = {}
    scraped_map = {}
    
    claims_to_search = [c for c in state["claims"] if state.get("queries", {}).get(c.id)]
    
    new_logs = []
    if claims_to_search:
        logger.info(f"Searching evidence for {len(claims_to_search)} claims")
        results = await asyncio.gather(*[agent.run(c.id, state["queries"][c.id], c.text) for c in claims_to_search])
        for claim, (artifacts, cached, excluded) in zip(claims_to_search, results):
            if cached:
                logger.info(f"Claim {claim.id}: Found {len(cached)} cached evidences")
                cached_evidences_map[claim.id] = cached
                new_logs.append(f"📦 Claim '{claim.id[:8]}...': Found {len(cached)} matches in ChromaDB.")
            if artifacts:
                logger.info(f"Claim {claim.id}: Found {len(artifacts)} web search artifacts")
                evidence_keys_map[claim.id] = artifacts
                new_logs.append(f"🌐 Claim '{claim.id[:8]}...': Initialized web search for {len(artifacts)} sources.")
                scraped_map[claim.id] = [a["url"] for a in artifacts]
            excluded_map[claim.id] = excluded
    else:
        logger.info("No queries available for evidence retrieval")
        new_logs.append("ℹ️ No queries to process for evidence.")
        
    return {
        "raw_evidence_keys": evidence_keys_map, 
        "evidences": cached_evidences_map,
        "excluded_sources": excluded_map,
        "scraped_sources": scraped_map,
        "logs": new_logs}

async def isolate_passages_node(state: WorkflowState):
    """Isolate passages from raw web content."""
    logger = WorkflowLogger.get_logger("isolate_node", state.get("trace_id", "N/A"))
    logger.info("Isolating passages from raw web content")
    agent = PassageIsolationAgent()
    isolated_evidences_map = {}
    claims_to_process = [c for c in state["claims"] if c.id in state.get("raw_evidence_keys", {})]
    
    new_logs = []
    if claims_to_process:
        logger.info(f"Processing {len(claims_to_process)} claims with raw evidence")
        results = await asyncio.gather(*[agent.run(c, state["raw_evidence_keys"][c.id]) for c in claims_to_process])
        isolated_evidences_map = {c.id: evs for c, evs in zip(claims_to_process, results)}
        for c_id, evs in isolated_evidences_map.items():
            logger.info(f"Claim {c_id}: Isolated {len(evs)} passages")
            new_logs.append(f"✂️ Extracted {len(evs)} relevant passages from raw web content for claim '{c_id[:8]}...'.")
    else:
        logger.info("No raw evidence keys to process")
        
    return {"evidences": isolated_evidences_map, "logs": new_logs}

async def score_credibility_node(state: WorkflowState):
    """Score credibility of new isolated passages."""
    logger = WorkflowLogger.get_logger("credibility_node", state.get("trace_id", "N/A"))
    logger.info("Scoring credibility of isolated passages")
    agent = CredibilityAgent()
    updated_evidences_map = {}
    tasks = []
    claims_with_new_evidence = []
    new_logs = []
    
    for claim in state["claims"]:
        evs = state.get("evidences", {}).get(claim.id, [])
        if not evs: continue
            
        new_ev = [e for e in evs if e.lineage.get("source") != "chromadb"]
        cached_ev = [e for e in evs if e.lineage.get("source") == "chromadb"]
        
        if new_ev:
            logger.info(f"Claim {claim.id}: Scoring {len(new_ev)} new passages")
            claims_with_new_evidence.append((claim, cached_ev))
            tasks.append(agent.run(claim, new_ev))
        else:
            updated_evidences_map[claim.id] = cached_ev
            
    if tasks:
        results = await asyncio.gather(*tasks)
        for (claim, cached), newly_scored in zip(claims_with_new_evidence, results):
            all_evs = cached + newly_scored
            # Deduplicate by unique_id
            unique_evs = {e.unique_id: e for e in all_evs}.values()
            logger.info(f"Claim {claim.id}: Finished scoring. Total unique evidence count: {len(unique_evs)}")
            updated_evidences_map[claim.id] = list(unique_evs)
            new_logs.append(f"⚖️ Scored {len(newly_scored)} new passages for '{claim.id[:8]}...'.")
    else:
        logger.info("No new passages to score")
            
    return {"evidences": updated_evidences_map, "logs": new_logs}

async def persist_evidence_node(state: WorkflowState):
    """Persist new high-quality evidence back to ChromaDB."""
    logger = WorkflowLogger.get_logger("persist_node", state.get("trace_id", "N/A"))
    logger.info("Persisting high-quality evidence to ChromaDB")
    store = ChromaStore()
    persisted_map = {}
    persisted_count = 0
    for claim_id, evidences in state.get("evidences", {}).items():
        persisted_for_claim = [ev for ev in evidences if ev.lineage.get("source") != "chromadb" and ev.credibility_score >= 0.7]
        for ev in persisted_for_claim:
            store.upsert_evidence(claim_id, ev)
            persisted_count += 1
        if persisted_for_claim:
            persisted_map[claim_id] = persisted_for_claim
            
    
    logger.info(f"Persisted {persisted_count} new high-quality evidences")
    return {
        "persisted_evidences": persisted_map,
        "logs": [f"💾 Persisted {persisted_count} high-quality sources to long-term memory."]
        }

async def ensemble_decision_node(state: WorkflowState):
    """Reach ensemble verdicts."""
    logger = WorkflowLogger.get_logger("ensemble_node", state.get("trace_id", "N/A"))
    logger.info("Reaching ensemble verdicts for claims")
    agent = EnsembleDecisionAgent()
    tasks = [agent.run(c, state.get("evidences", {}).get(c.id, [])) for c in state["claims"]]
    results = await asyncio.gather(*tasks)
    
    verdicts = {c.id: r for c, r in zip(state["claims"], results)}
    for c_id, report in verdicts.items():
        logger.info(f"Claim {c_id}: Verdict reached -> {report.verdict.value}")
        
    return {"verdicts": verdicts, "logs": [f"🤝 Reached consensus for {len(verdicts)} claims using ensemble logic."]}

async def synthesize_report_node(state: WorkflowState):
    """Synthesize final reports and summary."""
    logger = WorkflowLogger.get_logger("synthesize_node", state.get("trace_id", "N/A"))
    logger.info("Synthesizing final report")
    agent = VerificationAgent()
    claims_to_verify = [c for c in state["claims"] if c.id in state.get("verdicts", {})]
    
    if not claims_to_verify:
        logger.warning("No claims identified for verification")
        return {"final_output": "No claims were identified for verification.", "logs": ["⚠️ Workflow ended with no verifiable claims."]}

    logger.info(f"Verifying {len(claims_to_verify)} claims")
    results = await asyncio.gather(*[agent.run(c, state["verdicts"][c.id]) for c in claims_to_verify])
    final_verdicts_map = {c.id: r for c, r in zip(claims_to_verify, results)}
        
    summary_parts = ["### Multi-Agent Fact-Checking Report\n"]
    for claim in state["claims"]:
        report = final_verdicts_map.get(claim.id)
        if report:
            verdict_label = report.verdict.value.upper()
            summary_parts.append(f"**[{verdict_label}] Claim:** {claim.text}")
            summary_parts.append(f"\n**Verdict:** {verdict_label} (Confidence: {report.confidence})")
            summary_parts.append(f"\n**Rationale:** {report.rationale}")
            if report.correction:
                summary_parts.append(f"**Correction:** {report.correction}")
            summary_parts.append("\n---\n")
    
    logger.info("Final report synthesis complete")
    return {"verdicts": final_verdicts_map, "final_output": "\n".join(summary_parts), "logs": ["📝 Final report synthesized."]}

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
