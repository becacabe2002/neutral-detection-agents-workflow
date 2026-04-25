from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from src.models.evidence import Evidence
from src.models.claim import Claim
from src.services.redis_cache import RedisCache
from src.services.mbfc_registry import MBFCRegistry
from src.utils.domain_parser import canonicalize_domain
from src.config import settings

class PassageExtraction(BaseModel):
    relevant_passage: Optional[str] = Field(None, description="The exact excerpt supporting or refuting the claim")
    found: bool = Field(..., description="Whether relevant information was found")

SYSTEM_PROMPT = """
You are a Passage Isolation Agent. You will be given a factual claim and a large block of text.
Your task is to extract the EXACT sentence or passage that directly supports or contradicts the claim.
If the text contains no relevant information, set found to false.
DO NOT SUMMARIZE, provide the raw excerpt.
"""

class PassageIsolationAgent:
    def __init__(self, model: str = settings.ISOLATION_MODEL):
        self.llm = ChatGoogleGenerativeAI(
            model=model,
            api_key=settings.GOOGLE_API_KEY,
            temperature=0
        ).with_structured_output(PassageExtraction)

        self.cache = RedisCache()
        self.mbfc = MBFCRegistry()
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("user", "CLAIM: {claim_text}\n\nTEXT:\n{raw_text}")
        ])
        self.chain = self.prompt | self.llm

    async def run(self, claim: Claim, artifacts: List[dict]) -> List[Evidence]:
        evidences = []
        for art in artifacts:
            url = art["url"]
            key = art["redis_key"]

            # Fetch site content from redis
            payload = self.cache.get_payload(key)
            if not payload or not isinstance(payload, dict):
                continue

            raw_text = payload.get("text", "")
            if not raw_text:
                continue

            result: PassageExtraction = await self.chain.ainvoke({
                "claim_text": claim.text,
                "raw_text": raw_text[:200000]
            })

            if result.found and result.relevant_passage:
                profile = self.mbfc.lookup_domain(url)
                if not profile:
                    continue
                
                published_at = None
                raw_date = payload.get("published_at")
                if raw_date:
                    try:
                        # Attempt to let Pydantic handle it, but catch if it fails
                        # We create a dummy model just to check the date
                        class DateCheck(BaseModel):
                            d: datetime
                        DateCheck(d=raw_date)
                        published_at = raw_date
                    except Exception:
                        published_at = None
                
                evidences.append(Evidence(
                    source_url=url,
                    source_domain=canonicalize_domain(url),
                    published_at=published_at,
                    excerpt=result.relevant_passage,
                    source_profile=profile,
                    credibility_score=0.0, # will be update in next node
                    lineage={"key": key}
                ))
        return evidences
