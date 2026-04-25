import hashlib
from typing import List, Optional
from pydantic import BaseModel, Field
from src.agents.base import BaseAgent
from src.models.claim import Claim, ClaimType
from src.config import settings

class ClaimDraft(BaseModel):
    # claim without id, used for internal model
    text: str = Field(..., description="The atomic factual claim text")
    type: ClaimType = Field(default=ClaimType.ATOMIC)
    verifiable: bool = Field(..., description="Whether the claim can be objectively proven or disproven")
    timestamp_context: Optional[str] = Field(None, description="Temporal context like 'in 2025' or 'March 2024'")

class ClaimDecompositionOuput(BaseModel):
    # extracted list of claim draft
    claims: List[ClaimDraft]


SYSTEM_PROMPT = """
You are a Claim Decomposition Agent. Your task is to analyze the input text and extract all factual claims that can be objectively verified.

Follow these rules:
1. Split compound sentences into atomic subclaims.
2. For each claim, determine if it is verifiable or not.
3. Identify the claim type (atomic, compound, or non_verifiable)
4. Extract any temporal context (e.g., "in 2025").
5. If a statement is a subjective opinion, a value judgment, or a personal preference, mark it as non_verifiable.
6. Common myths, urban legends, and potentially false factual statements ARE verifiable and MUST be marked as verifiable=True so they can be fact-checked.
7. Focus on whether a claim *could* be proven or disproven by evidence, regardless of whether you suspect it is true or false.

DO NOT GENERATE IDs. Focus on the claim text and metadata.
"""

class ClaimDecompositionAgent(BaseAgent):
    def __init__(self, model: str = settings.DEFAULT_LLM_MODEL):
        super().__init__(
            model_name=model, 
            structured_output=ClaimDecompositionOuput
        )
        
        from langchain_core.prompts import ChatPromptTemplate
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("user", "{input_text}")
        ])

        self.chain = self.prompt | self.llm


    def _generate_id(self, text: str) -> str:
        """
        Generate an unique claim id from its text
        """
        clean_text = text.lower().strip()
        return hashlib.sha256(clean_text.encode()).hexdigest()[:16]
    
    async def run(self, input_text: str, trace_id: str = "N/A") -> List[Claim]:
        """
        Decompose input_text into atomic claims and assigns deterministic IDs.
        """
        logger = self.get_logger(trace_id)
        try:
            result: ClaimDecompositionOuput = await self.chain.ainvoke({"input_text": input_text})

            final_claims = []
            for draft in result.claims:
                claim_id = self._generate_id(draft.text)

                final_claims.append(Claim(
                    id = claim_id,
                    text=draft.text,
                    type= draft.type,
                    verifiable=draft.verifiable,
                    timestamp_context=draft.timestamp_context
                ))
            return final_claims
        except Exception as e:
            logger.error(f"Error in ClaimDecompositionAgent: {e}")
            fallback_id = self._generate_id(input_text)
            return [Claim(
                id=fallback_id,
                text=input_text,
                type=ClaimType.COMPOUND,
                verifiable=True
            )]
