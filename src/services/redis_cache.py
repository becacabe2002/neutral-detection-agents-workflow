import redis
import hashlib
import json
from typing import Dict, Any, Optional
from src.config import settings

class RedisCache:
    def __init__(self, url: str = settings.REDIS_URL):
        self.client = redis.from_url(url, decode_responses=True)

    def _generate_key(self, claim_id: str, url: str) -> str:
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return f"scrape:{claim_id}:{url_hash}"
    
    def set_payload(self, claim_id: str, url: str, payload: Dict[str, Any]):
        key = self._generate_key(claim_id, url)
        # Store as JSON string
        self.client.set(key, json.dumps(payload), ex=settings.REDIS_TTL) 
        return key
    
    def get_payload(self, key: str) -> Optional[Dict[str, Any]]:
        raw = self.client.get(key)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Fallback for old string-only cache entries if they exist
            return {"text": raw, "published_at": None}
    