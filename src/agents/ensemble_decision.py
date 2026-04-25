from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from src.models.evidence import Evidence
from src.models.report import VerdictReport, Verdict, UncertaintyType, ConflictDetails
from src.models.claim import Claim
from src.config import settings

class ConsensusResult(BaseModel):
    is_contradictory: bool = Field(..., description="True if evidence pieces flatly contradict each other")
    explanation: str = Field(..., description="Detailed explanation of the consensus or contradiction")
    conflicting_ids: List[str] = Field(default_factory=list, description="List of source URLs that are in conflict")
    suggested_verdict: Verdict = Field(..., description="The verdict based on pure semantic consensus")

SYSTEM_PROMPT = """
You are a Consensus Analyst. Compare multiple pieces of evidence against a claim.
Your task are:
* Identify if there are flat contradictions (mutually exclusive facts) between high-credibility sources.
* If contradictory, specify which URLs conflict.
"""

class EnsembleDecisionAgent:
    def __init__(self, model: str = settings.DEFAULT_LLM_MODEL):
        self.llm = ChatOpenAI(
            model=model,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.2
        ).with_structured_output(ConsensusResult)

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("user", "CLAIM: {claim}\n\nEVIDENCE:\n{evidence_text}")
        ])

        self.chain = self.prompt | self.llm

    async def run(self, claim: Claim, evidences: List[Evidence]) -> VerdictReport:
        # check for exist of evidences
        if not evidences:
            return VerdictReport(
                claim_id=claim.id,
                verdict=Verdict.UNCERTAIN,
                confidence=0.0,
                rationale="No credible evidence was found for this claim.",
                uncertainty_type=UncertaintyType.INSUFFICIENT_EVIDENCE
            )

        # Strict Consensus Check (Pairwise/Global Contradiction Detection)
        evidence_text = "\n---\n".join([
            f"URL: {e.source_url}\nExcerpt: {e.excerpt}\n" for e in evidences[:10]
        ])
        
        consensus: ConsensusResult = await self.chain.ainvoke({
            "claim": claim.text,
            "evidence_text": evidence_text
        })

        # handle if there is contradicts in evidences
        if consensus.is_contradictory:
            return VerdictReport(
                claim_id=claim.id,
                verdict=Verdict.UNCERTAIN,
                confidence=0.4, # Low confidence due to conflict
                rationale=consensus.explanation,
                citations=evidences,
                uncertainty_type=UncertaintyType.CONTRADICTORY_EVIDENCE,
                conflict_details=ConflictDetails(
                    primary_contradiction=consensus.explanation,
                    conflicting_evidence_ids=consensus.conflicting_ids
                )
            )

        # Calculate Weighted Fusion Logic
        # Final Score = Σ (Signal_i * Weight_i) / N + Quantity Boost
        total_score = 0.0
        for ev in evidences:
            # credibility_score already includes Reliability * Entailment
            total_score += ev.credibility_score

        avg_score = total_score / len(evidences)
        
        # Quantity boost: +10% per unique domain, max +30%
        unique_domains = len(set(e.source_domain for e in evidences))
        quantity_boost = min(0.3, unique_domains * 0.05)
        
        final_confidence = min(1.0, avg_score + quantity_boost)

        # Determine Verdict based on Thresholds
        if final_confidence >= 0.65:
            verdict = Verdict.SUPPORTED
        elif final_confidence <= 0.45:
            verdict = Verdict.NOT_SUPPORTED
        else:
            verdict = Verdict.UNCERTAIN

        return VerdictReport(
            claim_id=claim.id,
            verdict=verdict,
            confidence=round(final_confidence, 2),
            rationale=consensus.explanation,
            citations=evidences,
            uncertainty_type=UncertaintyType.NONE if verdict != Verdict.UNCERTAIN else UncertaintyType.INSUFFICIENT_EVIDENCE
        )