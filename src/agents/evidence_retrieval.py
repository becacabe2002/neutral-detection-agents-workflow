from typing import List, Dict
from src.services.web_search import WebSearchService
from src.services.web_scraper import WebScraper
from src.services.mbfc_registry import MBFCRegistry
from src.services.redis_cache import RedisCache
from src.config import settings

class EvidenceRetrievalAgent:
    def __init__(self):
        self.search_service = WebSearchService()
        self.scraper = WebScraper()
        self.cache = RedisCache()
        self.mbfc = MBFCRegistry()

    async def run(self, claim_id: str, queries: List[str]) -> List[dict]:
        all_urls = set()
        for query in queries:
            urls = self.search_service.search(query)
            all_urls.update(urls)
        
        redis_keys = []
        total_search_results = settings.MAX_QUERIES_PER_CLAIMS * settings.MAX_SEARCH_RESULTS
        artifacts = []
        for url in list(all_urls)[:total_search_results]:
            # MBFC Pre-flight check
            if not self.mbfc.is_trusted(url):
                continue
            try:
                payload = self.scraper.scrape(url)
                # payload is now {"text": str, "published_at": Optional[str]}
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
        return artifacts

