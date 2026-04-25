import logging
from typing import Type, TypeVar, Optional, Any, Dict
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from src.config import settings
from src.utils.logger import WorkflowLogger

# Global singleton storage for services to prevent redundant heavy initializations (e.g. Embedding models)
_SHARED_SERVICES: Dict[Any, Any] = {}

T = TypeVar("T", bound=BaseModel)

class BaseAgent:
    """
    Base class for all agents in the Fact-Checking workflow.
    Provides centralized LLM initialization, lazy-loaded shared services, and standardized logging.
    """
    def __init__(
        self, 
        model_name: str = settings.DEFAULT_LLM_MODEL, 
        temperature: float = 0, 
        structured_output: Optional[Type[T]] = None
    ):
        self.model_name = model_name
        
        # 1. Initialize LLM with provider routing
        if "gemini" in model_name.lower():
            self.llm = ChatGoogleGenerativeAI(
                model=model_name, 
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=temperature
            )
        else:
            self.llm = ChatOpenAI(
                model=model_name, 
                api_key=settings.OPENAI_API_KEY, 
                temperature=temperature
            )
        
        if structured_output:
            self.llm = self.llm.with_structured_output(structured_output)

    def _get_service(self, service_class):
        """Lazy-load and cache service instances to be shared across all child agents."""
        if service_class not in _SHARED_SERVICES:
            # Note: Using class-based initialization. 
            # If your services require specific arguments, consider a factory registry.
            _SHARED_SERVICES[service_class] = service_class()
        return _SHARED_SERVICES[service_class]

    # Shared Service Accessors (Inherited by all agents)
    @property
    def mbfc(self):
        from src.services.mbfc_registry import MBFCRegistry
        return self._get_service(MBFCRegistry)

    @property
    def chroma(self):
        from src.services.chroma_store import ChromaStore
        return self._get_service(ChromaStore)

    @property
    def cache(self):
        from src.services.redis_cache import RedisCache
        return self._get_service(RedisCache)

    @property
    def scraper(self):
        from src.services.web_scraper import WebScraper
        return self._get_service(WebScraper)

    @property
    def search_service(self):
        from src.services.web_search import WebSearchService
        return self._get_service(WebSearchService)

    def get_logger(self, trace_id: str = "N/A"):
        """Returns a logger instance scoped to the agent name."""
        return WorkflowLogger.get_logger(self.__class__.__name__, trace_id)
