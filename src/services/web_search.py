from typing import List
from ddgs.ddgs import DDGS
from src.config import settings

class WebSearchService:
    def __init__(self, proxy: str = settings.DDGS_PROXY):
        self.proxy = proxy

    def search(self, query: str, max_results: int = settings.MAX_SEARCH_RESULTS) -> List[str]:
        with DDGS(proxy=self.proxy) as ddgs:
            results = ddgs.text(query, max_results=max_results)
            return [r['href'] for r in results] if results else []