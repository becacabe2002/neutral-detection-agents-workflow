import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    MBFC_DB_PATH: str = os.getenv("MBFC_SQLITE_PATH", "data/mbfc.sqlite")

    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_TTL: int = 900

    CHROMA_PATH: str = os.getenv("CHROMA_DB_PATH", "data/chroma_db")

    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    RETRIEVAL_INSTRUCTION: str = "Represent this sentence for searching relevant passages: "

    DDGS_PROXY: str = os.getenv("DDGS_PROXY", "http://localhost:5566") # rotating tor proxy
    MAX_SEARCH_RESULTS: int = 10
    MAX_QUERIES_PER_CLAIMS: int = 5

settings = Settings()