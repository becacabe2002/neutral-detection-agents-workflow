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
            "Bias": ev.source_profile.bias_classification.value,
            "URL": ev.source_url
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
        "errors": []
    }
    
    with st.status("🔍 Agents are working...", expanded=True) as status:
        st.write("🎬 Initializing workflow...")
        # Since app_workflow is a compiled LangGraph, we use astream or invoke
        # We'll use invoke for simplicity in this MVP UI
        final_state = await app_workflow.ainvoke(initial_state)
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
            with st.expander(f"Claim: {claim.text}", expanded=True):
                verdict: VerdictReport = result_state.get("verdicts", {}).get(claim.id)
                
                if not verdict:
                    st.write("No verdict reached for this claim.")
                    continue
                
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
                    st.write(verdict.conflict_details.get("primary_contradiction", "Multiple sources provide conflicting data."))
                    
                    # Display conflicting IDs if available (Logic would map them to evidence list)
                    # For MVP, we show all evidence and highlight conflicts in rationale
                
                # Citations Table
                ev_list = result_state.get("evidences", {}).get(claim.id, [])
                if ev_list:
                    st.markdown("**Citations:**")
                    df = format_evidence_table(ev_list)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    
                    for ev in ev_list:
                        with st.popover(f"Excerpt from {ev.source_domain}"):
                            st.write(ev.excerpt)
                            st.caption(f"Lineage: {ev.lineage}")
                else:
                    st.info("No credible evidence found for this subclaim.")

st.divider()
st.caption("Neutral Detection Agents Workflow | Built with LangGraph & Streamlit")
