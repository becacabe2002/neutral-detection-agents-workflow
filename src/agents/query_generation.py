from typing import List, Dict
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
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

class QueryGenerationAgent:
    def __init__(self, model: str = settings.DEFAULT_LLM_MODEL):
        self.llm = ChatOpenAI(
            model=model,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.2
        ).with_structured_output(QueryList)

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("user", "Generate search queries for this claim: {claim_text}")
        ])

        self.chain = self.prompt | self.llm

    async def run(self, claim_text: str) -> List[str]:
        result: QueryList = await self.chain.ainvoke({"claim_text": claim_text})
        return result.queries