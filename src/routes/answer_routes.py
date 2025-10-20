# src/routes/answer_routes.py
if True:
    pass  # file intentionally inert during debugging

from flask import request, jsonify
from flask import request, jsonify
import traceback

# CLASS import (your file is src/ai/explanation_generator.py)
from src.ai.explanation_generator import ExplanationGenerator

# OPTIONAL: if you have a helper to fetch full details by PMID, wire it here.
# We'll try several likely paths/names; if none import, we just skip the fetch.
try:
    from src.app.services.paper_service import fetch_article_details as fetch_by_pmids  # function
except Exception:
    try:
        from src.app.services.paper_service import fetch_article_details as fetch_by_pmids
    except Exception:
        fetch_by_pmids = None

def init_answer_routes(app):
    @app.route("/explain-research", methods=["POST"])
    def explain_research():
        data = request.get_json(silent=True) or {}
        try:
            query  = (data.get("query") or "").strip()
            pmids  = data.get("pmids")  or []
            papers = data.get("papers") or []
            if not query:
                return jsonify({"error": "missing query"}), 400

            # 1) Normalize papers: ensure 'abstract' exists (use 'snippet' as fallback)
            norm = []
            for p in papers:
                if not isinstance(p, dict):
                    continue
                p = p.copy()
                if not p.get("abstract") and p.get("snippet"):
                    p["abstract"] = p["snippet"]
                # keep core fields tidy
                p["pmid"]    = str(p.get("pmid") or p.get("PMID") or "")
                p["title"]   = p.get("title")   or ""
                p["journal"] = p.get("journal") or p.get("source") or ""
                p["year"]    = p.get("year")    or p.get("pubyear") or p.get("publication_year")
                norm.append(p)
            papers = norm

            # 2) If we still have no usable text, try fetching details by PMID (if helper exists)
            have_text = any((p.get("abstract") or p.get("title")) for p in papers)
            if (not have_text) and pmids and fetch_by_pmids:
                try:
                    details = fetch_by_pmids(pmids)  # must return list[dict]
                    norm2 = []
                    for r in details or []:
                        norm2.append({
                            "pmid": str(r.get("pmid") or r.get("PMID") or ""),
                            "title": r.get("title") or "",
                            "journal": r.get("journal") or r.get("source") or "",
                            "year": r.get("year") or r.get("publication_year"),
                            "abstract": r.get("abstract") or r.get("snippet") or "",
                        })
                    papers = norm2 or papers
                except Exception as _e:
                    app.logger.warning("PMID fetch skipped: %s", _e)

            # 3) Build the research_content payload the generator expects
            research_content = {
                "query": query,
                "papers": papers,   # each with at least title/abstract when possible
                "pmids": pmids,
            }

            gen = ExplanationGenerator()
            result = gen.generate_layered_explanation(research_content)
            # Your generator returns a dict with keys like:
            #   technical_summary, simple_explanation, key_points, follow_up_questions

            # 4) Compose a single answer for the UI
            explanation_parts = []
            if isinstance(result, dict):
                if result.get("technical_summary"):
                    explanation_parts.append("Technical summary:\n" + result["technical_summary"])
                if result.get("simple_explanation"):
                    explanation_parts.append("\nPlain-language explanation:\n" + result["simple_explanation"])
                if result.get("key_points"):
                    bullets = "\n".join(f"• {pt}" for pt in result["key_points"])
                    explanation_parts.append("\nKey points:\n" + bullets)
                if result.get("follow_up_questions"):
                    qs = "\n".join(f"• {q}" for q in result["follow_up_questions"])
                    explanation_parts.append("\nFollow-up questions:\n" + qs)
                explanation_text = "\n\n".join(explanation_parts).strip()
            else:
                explanation_text = str(result or "").strip()

            return jsonify({
                "success": True,
                "explanation": explanation_text,
                "used_pmids": pmids,
                "gen_latency_ms": 0
            })

        except Exception as e:
            app.logger.error("explain_research error: %s", e)
            app.logger.error("TRACE:\n%s", traceback.format_exc())
            return jsonify({"error": str(e)}), 500


