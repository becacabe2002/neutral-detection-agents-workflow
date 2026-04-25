from typing import List, Dict, Annotated, TypedDict
import operator
from src.models.claim import Claim
from src.models.evidence import Evidence
from src.models.report import VerdictReport

class ScrapeArtifact(TypedDict):
    url: str
    redis_key: str

class WorkflowState(TypedDict):
    """
    Central state object for the LangGraph workflow
    """
    # raw input from user 
    input_text: str
    # extracted atomic claims
    claims: Annotated[List[Claim], operator.add]

    # map claim id -> their seo queries
    queries: Dict[str, List[str]]

    # map claim id -> redis keys of raw scraped text
    raw_evidence_keys: Dict[str, List[ScrapeArtifact]]

    # map claim id -> list of refined Evidence objects
    evidences: Dict[str, List[Evidence]]

    # map claim id -> Final verdict report
    verdicts: Dict[str, VerdictReport]

    # Final synthesized summary
    final_output: str
    errors: Annotated[List[str], operator.add]

