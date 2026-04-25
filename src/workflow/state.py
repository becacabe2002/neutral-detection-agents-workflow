from typing import List, Dict, Annotated, TypedDict
import operator
from src.models.claim import Claim
from src.models.evidence import Evidence
from src.models.report import VerdictReport

def merge_dicts(a: Dict, b: Dict) -> Dict:
    return {**a, **b}

class ScrapeArtifact(TypedDict):
    url: str
    redis_key: str

class WorkflowState(TypedDict):
    """
    Central state object for the LangGraph workflow
    """
    # trace id for logging
    trace_id: str
    # raw input from user 
    input_text: str
    
    # extracted atomic claims
    claims: Annotated[List[Claim], operator.add]

    # map claim id -> their seo queries
    queries: Annotated[Dict[str, List[str]], merge_dicts]

    # map claim id -> redis keys of raw scraped text
    raw_evidence_keys: Annotated[Dict[str, List[ScrapeArtifact]], merge_dicts]

    # map claim id -> list of refined Evidence objects
    evidences: Annotated[Dict[str, List[Evidence]], merge_dicts]

    # map claim id -> Final verdict report
    verdicts: Annotated[Dict[str, VerdictReport], merge_dicts]

    # Final synthesized summary
    final_output: str
    errors: Annotated[List[str], operator.add]
