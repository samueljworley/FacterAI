from typing import Dict, Any, Optional
import time
import json
from datetime import datetime

class CacheService:
    def __init__(self, cache_duration: int = 86400):  # Default 24 hours
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_duration = cache_duration

    def get_key(self, query: str, source: str) -> str:
        """Generate cache key from query and source"""
        return f"{source}:{query.lower().strip()}"

    def get(self, query: str, source: str) -> Optional[Dict[str, Any]]:
        """Get cached results if they exist and aren't expired"""
        key = self.get_key(query, source)
        if key in self.cache:
            cached_data = self.cache[key]
            if time.time() - cached_data['timestamp'] < self.cache_duration:
                return cached_data['data']
            else:
                del self.cache[key]
        return None

    def set(self, query: str, source: str, data: Dict[str, Any]):
        """Cache new results"""
        key = self.get_key(query, source)
        self.cache[key] = {
            'timestamp': time.time(),
            'data': data
        }

    def clear_expired(self):
        """Clear expired cache entries"""
        current_time = time.time()
        expired_keys = [
            key for key, value in self.cache.items()
            if current_time - value['timestamp'] > self.cache_duration
        ]
        for key in expired_keys:
            del self.cache[key] 