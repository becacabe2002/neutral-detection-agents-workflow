from typing import List
from tavily import TavilyClient
from src.config import settings

class WebSearchService:
    def __init__(self, tavily_key: str = settings.TAVILY_API_KEY):
        if not tavily_key:
            raise ValueError("TAVILY_API_KEY is required for web search fallback.")
        self.tavily_client = TavilyClient(api_key=tavily_key)

    def search(self, query: str, max_results: int = settings.MAX_SEARCH_RESULTS) -> List[str]:
        """Execute web search using Tavily API."""
        try:
            results = self.tavily_client.search(query=query, max_results=max_results)
            return [r['url'] for r in results.get('results', [])]
        except Exception as e:
            # In a production system, we would log this error properly
            return []