import streamlit as st
import asyncio
import uuid
import pandas as pd
from src.workflow.graph import app_workflow
from src.models.report import VerdictReport
from src.models.evidence import Evidence

# Page Config
st.set_page_config(
    page_title="Neutral Detection Agents - Fact Checker",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 Multi-Agent Fact-Checking System")
st.markdown("""
This system uses an ensemble of agents to decompose claims, retrieve evidence from ChromaDB and the Web, 
and produce verifiable verdicts with explainable uncertainty.
""")

# Sidebar for configuration/stats
with st.sidebar:
    st.header("System Configuration")
    st.info("Orchestration: LangGraph\n\nRetrieval: Hybrid (ChromaDB + Web)")
    if st.button("Clear Cache"):
        st.cache_data.clear()
        st.success("Cache cleared")

# Main Input
input_text = st.text_area(
    "Enter a statement or article to fact-check:",
    placeholder="e.g., 'Country X reduced inflation to 2% in 2025.'",
    height=150
)

def format_evidence_table(evidences: list[Evidence]):
    data = []
    for ev in evidences:
        data.append({
            "Source": ev.source_domain,
            "Credibility": f"{ev.credibility_score:.2f}",
            "Factual Reporting": ev.source_profile.factual_reporting.value,
            "Excerpt": ev.excerpt,
            "Bias": ev.source_profile.bias_classification.value,
            "URL": str(ev.source_url)
        })
    return pd.DataFrame(data)

async def run_fact_check(text: str):
    trace_id = str(uuid.uuid4())
    initial_state = {
        "trace_id": trace_id,
        "input_text": text,
        "claims": [],
        "queries": {},
        "raw_evidence_keys": {},
        "evidences": {},
        "verdicts": {},
        "final_output": "",
        "logs": [],
        "errors": [],
        "excluded_sources": {},
        "scraped_sources": {},
        "persisted_evidences": {}
    }
    
    with st.status("🔍 Agents are working...", expanded=True) as status:
        log_container = st.container()
        processed_logs = set()
        final_state = initial_state.copy()
        
        # Using astream to get live updates from LangGraph nodes
        async for event in app_workflow.astream(initial_state):
            # event is a dict where keys are node names and values are the returned state updates
            for node_name, state_update in event.items():
                # 1. Update UI logs
                if "logs" in state_update:
                    for log in state_update["logs"]:
                        if log not in processed_logs:
                            log_container.write(log)
                            processed_logs.add(log)
                
                status.update(label=f"⏳ {node_name.replace('_', ' ').title()} in progress...")

                # 2. Accumulate state
                for k, v in state_update.items():
                    if k == "logs":
                        final_state[k].extend(v)
                    elif isinstance(v, list) and k in final_state:
                        final_state[k].extend(v)
                    elif isinstance(v, dict) and k in final_state:
                        final_state[k].update(v)
                    else:
                        final_state[k] = v

        status.update(label="✅ Fact-check complete!", state="complete")
    
    return final_state

if st.button("Analyze Factuality", type="primary"):
    if not input_text.strip():
        st.warning("Please enter some text to analyze.")
    else:
        # Run workflow
        result_state = asyncio.run(run_fact_check(input_text))
        
        # Display Results
        st.divider()
        st.header("Analysis Results")
        
        if result_state.get("errors"):
            for err in result_state["errors"]:
                st.error(f"Error: {err}")
        
        # Summary View
        st.markdown(result_state.get("final_output", "No summary generated."))
        
        # Detailed Claims View
        st.subheader("Detailed Evidence Breakdown")
        
        for claim in result_state.get("claims", []):
            # 1. Include Time Context in Claim Header
            header = f"Claim: {claim.text}"
            if claim.timestamp_context:
                header += f" (Time Context: {claim.timestamp_context})"
                
            with st.expander(header, expanded=True):
                verdict: VerdictReport = result_state.get("verdicts", {}).get(claim.id)
                
                if not verdict:
                    st.write("No verdict reached for this claim.")
                else:
                    # Visual Verdict Badge
                    col1, col2, col3 = st.columns([1, 1, 2])
                    with col1:
                        color = {
                            "Supported": "green",
                            "Not Supported": "red",
                            "Uncertain": "orange"
                        }.get(verdict.verdict.value, "gray")
                        st.markdown(f"### :{color}[{verdict.verdict.value}]")
                    with col2:
                        st.metric("Confidence", f"{verdict.confidence:.2f}")
                    with col3:
                        if verdict.uncertainty_type.value != "none":
                            st.warning(f"Uncertainty: {verdict.uncertainty_type.value}")

                    st.markdown(f"**Rationale:** {verdict.rationale}")
                    
                    if verdict.correction:
                        st.info(f"**Suggested Correction:** {verdict.correction}")

                    # Conflict Comparison View
                    if verdict.uncertainty_type.value == "contradictory_evidence" and verdict.conflict_details:
                        st.subheader("⚖️ Conflict Comparison")
                        st.error(verdict.conflict_details.primary_contradiction or "Multiple sources provide conflicting data.")
                        
                        if verdict.conflict_details.conflicting_evidence_ids:
                            st.write("**Conflicting Sources:**")
                            for c_id in verdict.conflict_details.conflicting_evidence_ids:
                                st.caption(f"- {c_id}")

                # Diagnostic Tabs
                tab_ev, tab_diag, tab_memory = st.tabs(["📄 Isolated Evidence", "🔍 Search Diagnostics", "🧠 Long-term Memory"])

                with tab_ev:
                    # 5. List of isolated evidences
                    ev_list = result_state.get("evidences", {}).get(claim.id, [])
                    if ev_list:
                        st.markdown("**Pertinent Passages extracted from sources:**")
                        df = format_evidence_table(ev_list)
                        st.dataframe(df, width='stretch', hide_index=True)
                        
                        for ev in ev_list:
                            with st.popover(f"Excerpt from {ev.source_domain}"):
                                st.write(ev.excerpt)
                                st.caption(f"Lineage: {ev.lineage}")
                    else:
                        st.info("No relevant evidence isolated for this subclaim.")

                with tab_diag:
                    # 2. Queries list
                    st.markdown("**Generated Search Queries:**")
                    queries = result_state.get("queries", {}).get(claim.id, [])
                    if queries:
                        for q in queries:
                            st.code(q, language=None)
                    else:
                        st.write("No queries generated.")

                    col_ex, col_sc = st.columns(2)
                    with col_ex:
                        # 3. List of search domains excluded
                        st.markdown("❌ **Excluded (Pre-flight Check Fail):**")
                        excluded = result_state.get("excluded_sources", {}).get(claim.id, [])
                        if excluded:
                            for url in excluded:
                                st.caption(url)
                        else:
                            st.write("None")
                    with col_sc:
                        # 4. List of scraped domains
                        st.markdown("✅ **Scraped Domains:**")
                        scraped = result_state.get("scraped_sources", {}).get(claim.id, [])
                        if scraped:
                            for url in scraped:
                                st.caption(url)
                        else:
                            st.write("None")

                with tab_memory:
                    # 6. List of strong evidences saved in chromadb
                    persisted = result_state.get("persisted_evidences", {}).get(claim.id, [])
                    if persisted:
                        st.success(f"Saved {len(persisted)} high-quality passages to long-term memory (ChromaDB).")
                        st.dataframe(format_evidence_table(persisted), hide_index=True)
                    else:
                        st.info("No new high-quality evidence (score >= 0.7) was persisted for this claim.")

st.divider()
st.caption("Neutral Detection Agents Workflow | Built with LangGraph & Streamlit")
