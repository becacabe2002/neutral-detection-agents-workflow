from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

class BiasClassification(str, Enum):
    EXTREME_LEFT = "Extreme Left Bias"
    LEFT = "Left Bias"
    LEFT_CENTER = "Left-Center Bias"
    LEAST_BIASED = "Least Biased"
    RIGHT_CENTER = "Right-Center Bias"
    RIGHT = "Right Bias"
    EXTREME_RIGHT = "Extreme Right Bias"

class FactualReporting(str, Enum):
    VERY_HIGH = "Very High"
    HIGH = "High"
    MOSTLY_FACTUAL = "Mostly Factual"
    MIXED = "Mixed"
    LOW = "Low"
    VERY_LOW = "Very Low"

class CredibilityRating(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"

class SourceProfile(BaseModel):
    domain: str = Field(..., description="Canonical domain (ex: nytimes.com)")
    bias_classification: BiasClassification
    factual_reporting: FactualReporting
    credibility_assessment: CredibilityRating
    country: Optional[str] = None
    media_type: Optional[str] = None
    mbfc_url: Optional[HttpUrl] = None

class Evidence(BaseModel):
    source_url: HttpUrl
    source_domain: str
    published_at: Optional[datetime] = None
    # differ from credibility_assessment of Source
    # calculate by combining signals: 
    # Source reliability + Recency + Semantic Entailment
    credibility_score: float = Field(..., ge=0.0, le=1.0)
    # Isolated pertinent passage
    excerpt: str = Field(..., min_length=10)
    source_profile: SourceProfile = Field(..., description="Mandatory for validated evidence")
    # metadata dict
    lineage: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def apply_hard_reject_policy(self) -> "Evidence":
        """
        Reject sources with Low or Very Low factual reporting
        """
        rejected_scores = [FactualReporting.LOW, FactualReporting.VERY_LOW]
        if self.source_profile.factual_reporting in rejected_scores:
            raise ValueError(f"Hard Reject: {self.source_domain} has {self.source_profile.factual_reporting} factual reporting")
        return self
    
    @property
    def factual_weight(self) -> float:
        weights = {
            FactualReporting.VERY_HIGH: 1.0,
            FactualReporting.HIGH: 0.8,
            FactualReporting.MOSTLY_FACTUAL: 0.6,
            FactualReporting.MIXED: 0.4,
        }
        return weights.get(self.source_profile.factual_reporting, 0.0)