from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from .claim import Claim
from .evidence import Evidence

class Verdict(str, Enum):
    SUPPORTED = "Supported"
    NOT_SUPPORTED = "Not Supported"
    UNCERTAIN = "Uncertain"

class UncertaintyType(str, Enum):
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CONTRADICTORY_EVIDENCE = "contradictory_evidence"
    NONE = "none"

class AgentStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    INSUFFICIENT_DATA = "insufficient_data"
    SKIPPED = "skipped"

class ConflictDetails(BaseModel):
    primary_contradiction: str = Field(..., description="Summary of the disagreement")
    conflicting_evidence_ids: List[str] = Field(..., description="List of source URLs or IDs that conflict")

class VerdictReport(BaseModel):
    claim_id: str
    verdict: Verdict
    confidence: float = Field(..., ge=0.0, le=1.0)
    rationale: str = Field(..., description="Concise explanation for the verdict")
    citations: List[Evidence] = Field(default_factory=list)
    uncertainty_type: UncertaintyType = Field(default=UncertaintyType.NONE)
    conflict_details: Optional[ConflictDetails] = None
    correction: Optional[str] = Field(None, description="Corrected fact if Not Supported")

class AgentOutput(BaseModel):
    status: AgentStatus
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)