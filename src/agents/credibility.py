from typing import List
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from src.models.claim import Claim
from src.models.evidence import Evidence, FactualReporting
from src.config import settings

class EntailmentScore(BaseModel):
    score: float = Field(..., ge=0.0, le=1.0, description="0.0 = irrelevant, 1.0 = perfect relevance (confirms or refutes)")
    reasoning: str

SYSTEM_PROMPT = """
You are a Semantic Relevance Specialist. Compare the CLAIM to the EVIDENCE EXCERPT.
Score how directly the excerpt addresses the claim (either by supporting it OR refuting it) on a scale of 0.0 to 1.0.
- 1.0: Directly confirms OR directly refutes the claim with specific factual information.
- 0.5: Mentions the topic or entities but is neutral, ambiguous, or only partially relevant.
- 0.0: Totally irrelevant to the factual content of the claim.
"""

class CredibilityAgent: 
    def __init__(self, model: str = settings.DEFAULT_LLM_MODEL):
        self.llm = ChatOpenAI(
            model=model,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.2
        ).with_structured_output(EntailmentScore)

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("user", "CLAIM: {claim}\nEXCERPT: {excerpt}")
        ])

        self.chain = self.prompt | self.llm

    async def run(self, claim: Claim, evidences: List[Evidence]) -> List[Evidence]:
        validated_evidences = []

        for ev in evidences:
            if ev.source_profile.factual_reporting in [FactualReporting.LOW, FactualReporting.VERY_LOW]:
                continue

            result: EntailmentScore = await self.chain.ainvoke({
                "claim": claim.text,
                "excerpt": ev.excerpt
            })

            # calculate final cred score
            base_weight = ev.factual_weight
            final_score = base_weight * result.score

            ev.credibility_score = round(final_score, 2)
            ev.lineage["entailment_score"] = result.score
            ev.lineage["entailment_reasoning"] = result.reasoning

            validated_evidences.append(ev)
        return sorted(validated_evidences, key=lambda x: x.credibility_score, reverse=True)