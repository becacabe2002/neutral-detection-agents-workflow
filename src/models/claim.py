from enum import Enum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class ClaimType(str, Enum):
    ATOMIC = "atomic"
    COMPOUND = "compound"
    NON_VERIFIABLE = "non_verifiable" # ambiguous and contextual claims

class Claim(BaseModel):
    id: str = Field(..., description="Unique UUID or hash for the claim")
    text: str = Field(..., min_length=5, description="The raw text of the claim")
    type: ClaimType = Field(default=ClaimType.ATOMIC)
    verifiable: bool = Field(..., description="True if the claim can be objectively checked")
    timestamp_context: Optional[datetime] = Field(None, description="The time period the claim refers to (ex: 'in 2025')")
