from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from src.models.evidence import Evidence
from src.models.report import VerdictReport, Verdict, UncertaintyType, ConflictDetails
from src.models.claim import Claim
from src.config import settings

class ConsensusResult(BaseModel):
    is_contradictory: bool = Field(..., description="True if high-credibility sources flatly contradict EACH OTHER on the core facts.")
    is_refuted: bool = Field(..., description="True if high-credibility sources are internally consistent but collectively REFUTE the user's claim.")
    explanation: str = Field(..., description="Detailed explanation of the consensus, refutation, or contradiction.")
    conflicting_ids: List[str] = Field(default_factory=list, description="List of source URLs that are in conflict with each other.")
    suggested_verdict: Verdict = Field(..., description="The verdict based on pure semantic consensus.")

SYSTEM_PROMPT = """
You are a Consensus Analyst. Compare multiple pieces of evidence against a factual CLAIM.
Your tasks are:
1. **Analyze Support/Refutation**: Determine if the evidence collectively supports, refutes, or is neutral toward the claim.
2. **Identify Source Conflict**: Detect if high-credibility sources flatly contradict EACH OTHER (mutually exclusive facts).
3. **Determine Verdict**:
   - If sources agree the claim is false, set is_refuted=True and suggested_verdict='Not Supported'.
   - If sources disagree with each other on the facts, set is_contradictory=True and suggested_verdict='Uncertain'.
   - If sources agree with the claim, set suggested_verdict='Supported'.
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
        # check for existence of evidences
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

        # Case 1: Internal Contradiction (Sources disagree with each other)
        if consensus.is_contradictory:
            return VerdictReport(
                claim_id=claim.id,
                verdict=Verdict.UNCERTAIN,
                confidence=0.4, 
                rationale=consensus.explanation,
                citations=evidences,
                uncertainty_type=UncertaintyType.CONTRADICTORY_EVIDENCE,
                conflict_details=ConflictDetails(
                    primary_contradiction=consensus.explanation,
                    conflicting_evidence_ids=consensus.conflicting_ids
                )
            )
        
        # Case 2: Collective Refutation (Sources agree claim is false)
        if consensus.is_refuted:
            return VerdictReport(
                claim_id=claim.id,
                verdict=Verdict.NOT_SUPPORTED,
                confidence=0.85, # High confidence in refutation
                rationale=consensus.explanation,
                citations=evidences,
                uncertainty_type=UncertaintyType.NONE
            )

        # Case 3: Weighted Fusion (Supportive/Neutral/Mixed)
        total_score = 0.0
        for ev in evidences:
            total_score += ev.credibility_score

        avg_score = total_score / len(evidences)
        
        # Quantity boost: +10% per unique domain, max +30%
        unique_domains = len(set(e.source_domain for e in evidences))
        quantity_boost = min(0.3, unique_domains * 0.05)
        
        final_confidence = min(1.0, avg_score + quantity_boost)

        # Determine Verdict based on LLM suggestion and relevance-based confidence
        # We trust the LLM's categorical choice, but use the fusion logic for the score
        verdict = consensus.suggested_verdict
        
        # If the fusion logic shows extremely low evidence quality/relevance, force Uncertain
        if final_confidence < 0.35 and verdict != Verdict.UNCERTAIN:
            verdict = Verdict.UNCERTAIN

        return VerdictReport(
            claim_id=claim.id,
            verdict=verdict,
            confidence=round(final_confidence, 2),
            rationale=consensus.explanation,
            citations=evidences,
            uncertainty_type=UncertaintyType.NONE if verdict != Verdict.UNCERTAIN else UncertaintyType.INSUFFICIENT_EVIDENCE
        )