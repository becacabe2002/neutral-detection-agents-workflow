import chromadb
from chromadb.api.types import Documents, Embeddings, EmbeddingFunction
from src.config import settings
from src.models.evidence import Evidence
from sentence_transformers import SentenceTransformer
import torch
from typing import List, Optional, Dict, Any
from datetime import datetime

class BGEEmbedingFunction:
    """
    Custom embeding function which let ChromaDB uses custom embedding model
    """

    def __init__(self):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL, device=device)

    def __call__(self, input: Documents) -> Embeddings :
        embeddings = self.model.encode(input, normalize_embeddings=True)
        return embeddings.tolist()
        

class ChromaStore:
    def __init__(self, path: str = settings.CHROMA_PATH):
        self.client = chromadb.PersistentClient(path=path)

        # Setup embedding function
        self.embedding_fn = BGEEmbedingFunction()

        self.collection = self.client.get_or_create_collection(
            name="evidence_v1",
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )
    
    def upsert_evidence(self, claim_id: str, evidence: Evidence):
        """
        Stores or updates an Evidence obj in vector store
        """
        self.collection.upsert(
            ids=[f"{claim_id}_{evidence.source_domain}"],
            documents=[evidence.excerpt],
            metadatas=[{
                "claim_id": claim_id,
                "source_url": str(evidence.source_url),
                "source_domain": evidence.source_domain,
                "credibility_score": evidence.credibility_score,
                "factual_reporting": evidence.source_profile.factual_reporting.value,
                "bias": evidence.source_profile.bias_classification.value,
                "ingested_at": datetime.now().isoformat()
            }]
        )

    def search_relevant(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """
        Performs a semantic search 
        """
        # BGE instruction
        formatted_query = f"{settings.RETRIEVAL_INSTRUCTION}{query}"
        return self.collection.query(
            query_texts=[formatted_query],
            n_results=n_results
        )
    
    def delete_by_claim(self, claim_id: str):
        """
        Cleans up evidence associated with a specific claim
        """
        self.collection.delete(where={"claim_id": claim_id})

    def get_stats(self):
        """
        Return number of documents in collection
        """
        return self.collection.count()