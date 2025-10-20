"""
ModelCache: Cache ML models to avoid initialization overhead
"""

import time
from typing import Optional, Any
import logging
import os
logger = logging.getLogger(__name__)
USE_EMBED  = os.getenv("USE_EMBED",  "0") == "1"   # SentenceTransformer
USE_RERANK = os.getenv("USE_RERANK", "0") == "1"   # CrossEncoder



class ModelCache:
    """Singleton cache for ML models"""
    
    _instance = None
    _models = {}
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def initialize_models(self):
        """Initialize all models once at startup"""
        if self._initialized:
            return
        
        self._models = getattr(self, "_models", {})
        start_time = time.time()

        # --- SentenceTransformer (optional) ---
        self._models["sentence_transformer"] = None
        if USE_EMBED:
            try:
                from sentence_transformers import SentenceTransformer
                self._models["sentence_transformer"] = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("✅ SentenceTransformer initialized")
            except Exception as e:
                logger.warning("Embeddings disabled — could not init SentenceTransformer: %s", e)
        else:
            logger.info("Embeddings disabled (USE_EMBED=0) — skipping SentenceTransformer")

        # --- CrossEncoder (optional) ---
        self._models["cross_encoder"] = None
        if USE_RERANK:
            try:
                from sentence_transformers import CrossEncoder
                self._models["cross_encoder"] = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
                logger.info("✅ CrossEncoder initialized")
            except Exception as e:
                logger.warning("Reranker disabled — could not init CrossEncoder: %s", e)
        else:
            logger.info("Reranker disabled (USE_RERANK=0) — skipping CrossEncoder")

        self._initialized = True
        logger.info("All models initialized in %.0fms", (time.time() - start_time) * 1000.0)
        return True

    
    def get_sentence_transformer(self):
        if not USE_EMBED:
            return None
        if not getattr(self, "_initialized", False):
            self.initialize_models()
        return self._models.get("sentence_transformer")

    def get_cross_encoder(self):
        if not USE_RERANK:
            return None
        if not getattr(self, "_initialized", False):
            self.initialize_models()
        return self._models.get("cross_encoder")

    
    def is_initialized(self):
        """Check if models are initialized"""
        return self._initialized

# Global instance
model_cache = ModelCache()
