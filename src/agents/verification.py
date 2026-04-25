from typing import List, Optional
from pydantic import BaseModel, Field
from src.agents.base import BaseAgent
from src.models.report import VerdictReport, Verdict, UncertaintyType
from src.models.evidence import Evidence
from src.models.claim import Claim
from src.config import settings

class VerificationAnalysis(BaseModel):
    final_rationale: str = Field(..., description="A comprehensive, user-friendly explanation of the verdict.")
    correction: Optional[str] = Field(None, description="If the claim is Not Supported, the actual fact discovered in the evidence.")
    logical_consistency_score: float = Field(..., ge=0.0, le=1.0, description="Confidence that the verdict is logically derived from citations.")

SYSTEM_PROMPT = """
You are a Final Verification Agent. Your goal is to synthesize the findings from multiple agents into a coherent report.
- Review the CLAIM, the CITATIONS, and the PRELIMINARY RATIONALE.
- Ensure the Rationale is clear, neutral, and directly references the provided evidence.
- If the verdict is 'Not Supported', try to provide a 'Correction' based on the provided citations.
- If the verdict is 'Uncertain', clearly explain why (e.g., conflicting evidence vs. missing data).
- CRITICAL: Never use your own internal knowledge to confirm, deny, or explain the claim if the verdict is 'Uncertain' due to 'insufficient_evidence'. In such cases, your rationale must only describe the failure to find credible evidence. Do not provide facts about the claim that are not present in the citations.
"""

class VerificationAgent(BaseAgent):
    def __init__(self, model: str = settings.DEFAULT_LLM_MODEL):
        super().__init__(
            model_name=model,
            temperature=0.2,
            structured_output=VerificationAnalysis
        )

        from langchain_core.prompts import ChatPromptTemplate
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("user", "CLAIM: {claim_text}\nVERDICT: {verdict}\nPRELIMINARY RATIONALE: {rationale}\nUNCERTAINTY TYPE: {uncertainty}\nCITATIONS:\n{citations_text}")
        ])

    async def run(self, claim: Claim, report: VerdictReport) -> VerdictReport:
        # Format citations for the LLM
        citations_text = ""
        if report.citations:
            citations_text = "\n---\n".join([
                f"Source: {c.source_domain} ({c.source_url})\nExcerpt: {c.excerpt}"
                for c in report.citations[:5] # Limit to top 5 for context window
            ])
        else:
            citations_text = "No citations available."

        # Run final analysis
        analysis: VerificationAnalysis = await (self.prompt | self.llm).ainvoke({
            "claim_text": claim.text,
            "verdict": report.verdict.value,
            "rationale": report.rationale,
            "uncertainty": report.uncertainty_type.value,
            "citations_text": citations_text
        })

        # Update report with synthesized information
        report.rationale = analysis.final_rationale
        report.correction = analysis.correction
        
        # Penalize confidence if logical consistency is low
        report.confidence = round(report.confidence * analysis.logical_consistency_score, 2)

        return report
