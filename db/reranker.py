from typing import List, Dict
# --- top of reranker module ---
import os, json, logging

logger = logging.getLogger(__name__)

# Feature flag so we can deploy lean first.
# Set USE_RERANK=1 later (and add sentence-transformers/torch to requirements)
USE_RERANK = os.getenv("USE_RERANK", "0") == "1"
CrossEncoder = None
if USE_RERANK:
    try:
        from sentence_transformers import CrossEncoder
    except Exception as e:
        logger.warning("Reranker disabled; could not import sentence_transformers: %s", e)
        CrossEncoder = None


class SearchReranker:
    def __init__(self):
        self._model = None
        logger.info("Reranker %s", "ENABLED" if (USE_RERANK and CrossEncoder) else "DISABLED")

    def _ensure_model(self):
        if not (USE_RERANK and CrossEncoder):
            return False
        if self._model is None:
            try:
                logger.debug("Loading CrossEncoder…")
                self._model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            except Exception as e:
                logger.error("Failed to load CrossEncoder: %s", e)
                self._model = None
                return False
        return True

    def rerank_results(self, query: str, papers: List[Dict], top_k: int = 5) -> List[Dict]:
        if not papers:
            return []
        if not self._ensure_model():
            return papers[:top_k]

        try:
            pairs, scored = [], []
            for p in papers:
                meta = p.get("metadata", {})
                if isinstance(meta, str):
                    try: meta = json.loads(meta)
                    except Exception: meta = {}
                p["_citation_count"] = int(meta.get("citation_count", 0))
                text = f"Title: {p.get('title','')}\nAbstract: {p.get('abstract','')}"
                pairs.append([query, text])

            scores = self._model.predict(pairs)
            for p, rel in zip(papers, scores):
                c = p.pop("_citation_count", 0)
                cscore = min(1.0, c/100.0)
                p["rerank_score"]     = 0.8*float(rel) + 0.2*cscore
                p["relevance_score"]  = float(rel)
                p["citation_score"]   = cscore
                p["citation_count"]   = c
                scored.append(p)

            return sorted(scored, key=lambda x: x["rerank_score"], reverse=True)[:top_k]
        except Exception as e:
            logger.error("Rerank error: %s", e)
            return papers[:top_k]
