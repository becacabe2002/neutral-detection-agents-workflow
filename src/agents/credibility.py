from enum import Enum
from typing import List
from pydantic import BaseModel, Field
from src.agents.base import BaseAgent
from src.models.claim import Claim
from src.models.evidence import Evidence, FactualReporting
from src.config import settings

class RelationshipType(str, Enum):
    SUPPORTS = "Supports"
    REFUTES = "Refutes"
    NEUTRAL_RELATED = "Neutral/Related"
    IRRELEVANT = "Irrelevant"

class EntailmentScore(BaseModel):
    reasoning: str = Field(..., description="Explain how the exerpt relates to the claim.")
    relationship: RelationshipType = Field(..., description="Categorize the relationship.")
    score: float = Field(..., ge=0.0, le=1.0, description="0.0 = irrelevant, 1.0 = perfect relevance (even if it confirms or refutes the claim)")

SYSTEM_PROMPT = """
You are a Semantic Relevance Specialist. Your job is to measure how much an EVIDENCE EXCERPT *address* a CLAIM, regardless of whether it proves the claim true or false.

CRITICAL ISNTRUCTION:
Do not confuse "Relevance" with "Truth". An excerpt that directly REFUTES the claim is highly relevant to fact-checking process of it, therefore must receive a high relevance score (near 1.0).

Follow these steps when addressing the excerpt:
1. Explain your reasoning: Analyze the excerpt against the claim. Does it support, refute or merely relate to the topic?
2. Categorize the relationship (SUPPORTS, REFUTES, NEUTRAL_RELATED or IRRELEVANT).
3. Assign a relevance score from 0.0 to 1.0:
- 1.0: Highly relevant (Directly SUPPORTS or directly REFUTES the claim)
- 0.5: Mentions the topic or entities but is neutral, ambiguous, or only partially relevant.
- 0.0: Totally irrelevant to the factual content of the claim.
"""

class CredibilityAgent(BaseAgent): 
    def __init__(self, model: str = settings.DEFAULT_LLM_MODEL):
        super().__init__(
            model_name=model,
            temperature=0.2,
            structured_output=EntailmentScore
        )

        from langchain_core.prompts import ChatPromptTemplate
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