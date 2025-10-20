# src/routes/search_routes.py
import logging
from src.app.services.planner import plan_query

import os
from src.embeddings.embedder import TextEmbedder
from src.embeddings.faiss_index import FAISSIndexManager
from src.app.services.paper_service import PaperService
from src.app.services.ai_service import AIService
# search_routes.py
from time import perf_counter
from flask import Blueprint, jsonify, request
import logging
log = logging.getLogger(__name__)
from src.app.services.paper_service import PaperService
from src.app.services.ai_service import AIService
  # <-- make sure this path matches your tree

search_bp = Blueprint("search", __name__)
paper_service = PaperService()
ai_service = AIService()  # shared instance
@search_bp.get("/healthz")
def healthz():
    return jsonify(ok=True), 200

@search_bp.route("/unified-search", methods=["POST"])
async def unified_search():
    
    try:
        data = request.get_json(silent=True) or {}
        print("unified_search payload:", data, flush=True)

        query = (data.get("query") or "").strip()
        if not query:
            return jsonify({"error": "bad_request", "detail": "query is required"}), 400
    
        query_type = (data.get("query_type") or "research").strip()
        plan = plan_query(query)
        log.info("[planner] %s", plan)

        requested = (data.get("query_type") or "auto").strip().lower()
        if requested in ("auto", "detect"):
            query_type = ai_service.classify_query_type(query)
        else:
            query_type = requested

        log.info("[unified] query=%r requested=%s => query_type=%s", query, requested, query_type)


        # 1) retrieval
        t0 = perf_counter()
        citations = await paper_service.search_papers(query=query, query_type=query_type)
        retrieval_ms = int((perf_counter() - t0) * 1000)

        rewritten = await ai_service.rewrite_query(query)
        if rewritten and rewritten != query:
            log.info("[rewrite] %r -> %r", query, rewritten)
        use_query = rewritten or query

        citations = await paper_service.search_papers(query=use_query, query_type=query_type)
        retrieval_ms = int((perf_counter() - t0) * 1000)

        # 2) optional summary
        want_summary = bool(data.get("want_summary")) or (query_type == "research")
        summary_text = ""
        summary_ms = 0
        if want_summary and citations:
            t1 = perf_counter()
            summary_text = await ai_service.summarize_citations(query, citations)
            summary_ms = int((perf_counter() - t1) * 1000)

        return jsonify({
            "success": True,
            "citations": citations,
            "retrieval_latency_ms": retrieval_ms,
            "summary_text": summary_text,
            "summary_latency_ms": summary_ms,
        }), 200

    except Exception as e:
        return jsonify({"error": "search_failed", "detail": str(e)}), 500



def init_semantic_search_routes(app):
    embedder = TextEmbedder(api_key=os.getenv("OPENAI_API_KEY"))
    index_manager = FAISSIndexManager(index_path="src/embeddings/research_index")
    index_manager.load()  # Load existing index

    @app.route("/api/research-search", methods=["POST"])
    def research_semantic_search():
        try:
            data = request.get_json()
            query = data.get("query")
            k = data.get("k", 5)

            if not query:
                return jsonify({"error": "No query provided"}), 400

            query_embedding = embedder.get_embedding(query)
            results = index_manager.search(query_embedding, k=k)

            return jsonify({
                "success": True,
                "query": query,
                "results": [{
                    "text": r["text"],
                    "pmid": r["pmid"],
                    "score": float(1 - r["distance"]),
                    "metadata": {
                        "authors": r.get("authors", []),
                        "year": r.get("year"),
                        "chunk_index": r.get("chunk_index"),
                    },
                } for r in results],
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
