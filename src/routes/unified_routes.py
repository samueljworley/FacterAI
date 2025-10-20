"""
Unified routes for the new system
"""
from flask import Blueprint, request, jsonify
import asyncio
from ..core.unified_controller import unified_controller
import os
from time import perf_counter
from flask import current_app
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
def _sources_block(docs):
    """Make a numbered list that matches your citation cards."""
    lines = []
    for i, d in enumerate(docs, 1):
        title = (d.get("title") or "").strip()
        first_author = (d.get("authors") or ["Unknown"])[0]
        journal = d.get("journal") or ""
        year = d.get("year") or ""
        lines.append(f"[{i}] {title} — {first_author}. {journal} {year}.")
    return "\n".join(lines)

def _make_detailed_answer(client, question, sources_block):
    """Ask the model for 2–4 paragraphs with bracketed [n] citations (no bullets)."""
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    prompt = f"""Using ONLY the numbered sources below, write 2–4 cohesive paragraphs that answer the question.
Insert bracketed numeric citations like [2] immediately after the facts they support. No bullets, no lists.
State uncertainties if evidence is indirect or mixed.

Question: {question}

Sources:
{sources_block}
"""
    r = client.chat.completions.create(
        model=model,
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}],
    )
    return r.choices[0].message.content.strip()

unified_bp = Blueprint('unified_routes', __name__)

def init_unified_routes(app):
    @app.route("/api/unified-search", methods=["POST"])
    def unified_search():
        data = request.get_json(silent=True) or {}
        query = data.get("query")
        query_type = data.get("query_type", "research")

        if not query:
            return jsonify({"error": "Query parameter is required"}), 400

        try:
            # Run the async function in the event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(unified_controller.process_query(query, query_type))
            loop.close()
            citations = result.get("citations") or []
            sources_block = _sources_block(citations)

            try:
                t0 = perf_counter()
                detailed_answer = _make_detailed_answer(client, query, sources_block)
                result["detailed_answer"] = detailed_answer
                result["detailed_latency_ms"] = int((perf_counter() - t0) * 1000)
            except Exception:
                current_app.logger.exception("detailed_answer generation failed")
                result["detailed_answer"] = ""
                result["detailed_latency_ms"] = 0

            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    app.register_blueprint(unified_bp)
