from typing import List
from pydantic import BaseModel, Field
from src.agents.base import BaseAgent
from src.config import settings

class QueryList(BaseModel):
    queries: List[str] = Field(..., min_length=1, max_length=5)

SYSTEM_PROMPT = f"""
You are an SEO-optimized Query Generation Agent. You goal is to generate {settings.MAX_QUERIES_PER_CLAIMS} highly targeted search queries for a given factual claim.

SEO strategies:
- Prioritize keyword density (entities, metrics, dates).
- Use search operators where effective (e.g., quotes for exact phrases).
- Create a mix of intent: Official stats, news reporting, and debunking/fact-check queries.
"""

class QueryGenerationAgent(BaseAgent):
    def __init__(self, model: str = settings.DEFAULT_LLM_MODEL):
        super().__init__(
            model_name=model,
            temperature=0.2,
            structured_output=QueryList
        )

        from langchain_core.prompts import ChatPromptTemplate
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("user", "Generate search queries for this input: \n {input_text}")
        ])

        self.chain = self.prompt | self.llm

    async def run(self, claim_text: str, timestamp_context: str = None) -> List[str]:
        input_text = f"Claim: {claim_text}"
        if timestamp_context:
            input_text += f" - Time Context: {timestamp_context}"
        result: QueryList = await self.chain.ainvoke({"input_text": input_text})
        return result.queries