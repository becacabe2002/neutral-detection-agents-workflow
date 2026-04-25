from typing import List, Dict, Tuple
from src.agents.base import BaseAgent
from src.models.evidence import Evidence
from src.config import settings

class EvidenceRetrievalAgent(BaseAgent):
    def __init__(self):
        # Initialize the base class. 
        # Note: This agent doesn't use an LLM directly, but inherits service access.
        super().__init__()

    async def run(self, claim_id: str, queries: List[str], claim_text: str) -> Tuple[List[dict], List[Evidence]]:
        """
        Retrieves evidence for a claim. 
        First checks ChromaDB for existing high-quality evidence.
        If found, returns immediately to skip web search.
        Otherwise, performs a web search and returns artifacts for scraping.
        """
        # 1. Local-First: Check ChromaDB for existing evidence
        cached_evidences = []
        try:
            chroma_results = self.chroma.search_relevant(claim_text, n_results=3)
            
            if chroma_results.get("documents") and len(chroma_results["documents"][0]) > 0:
                for i, doc in enumerate(chroma_results["documents"][0]):
                    meta = chroma_results["metadatas"][0][i]
                    # We need the source profile for downstream logic
                    profile = self.mbfc.lookup_domain(meta["source_url"])
                    if profile:
                        cached_evidences.append(Evidence(
                            source_url=meta["source_url"],
                            source_domain=meta["source_domain"],
                            excerpt=doc,
                            source_profile=profile,
                            credibility_score=meta["credibility_score"],
                            lineage={"source": "chromadb"} # Tag as cached
                        ))
                
                # If we found sufficient local evidence, return early
                if cached_evidences:
                    return [], cached_evidences
        except Exception as e:
            print(f"ChromaDB retrieval error: {e}")

        # 2. Web-Fallback: Only runs if ChromaDB returned nothing
        all_urls = set()
        for query in queries:
            try:
                urls = self.search_service.search(query)
                all_urls.update(urls)
            except Exception as e:
                print(f"Search error for query '{query}': {e}")
        
        total_search_results = settings.MAX_QUERIES_PER_CLAIMS * settings.MAX_SEARCH_RESULTS
        artifacts = []
        for url in list(all_urls)[:total_search_results]:
            # MBFC Pre-flight check
            if not self.mbfc.is_trusted(url):
                continue
            try:
                payload = self.scraper.scrape(url)
                if not payload.get("text") or len(payload["text"]) < 50:
                    continue
                redis_key = self.cache.set_payload(claim_id, url, payload)

                artifacts.append({
                    "url": url,
                    "redis_key": redis_key
                })
            except Exception as e:
                print(f"Failed to process {url}: {e}")
                continue
                
        return artifacts, []
