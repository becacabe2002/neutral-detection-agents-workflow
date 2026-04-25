import redis
import hashlib
from src.config import settings

class RedisCache:
    def __init__(self, url: str = settings.REDIS_URL):
        self.client = redis.from_url(url, decode_responses=True)

    def _generate_key(self, claim_id: str, url: str) -> str:
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return f"scrape:{claim_id}:{url_hash}"
    
    def set_payload(self, claim_id: str, url: str, text: str):
        key = self._generate_key(claim_id, url)
        self.client.set(key, text, ex=settings.REDIS_TTL) # overwrite policy
        return key
    
    def get_payload(self, key: str) -> str:
        return self.client.get(key)
    