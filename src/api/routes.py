from flask import Blueprint, request, jsonify
from typing import Dict, Any
from src.database.db_manager import DatabaseManager
from src.database.models import Paper
from config.config import config
from src.llm.openai_client import LLMClient
from src.clients.semantic_scholar import SemanticScholarClient
import logging
from ..clients.client_manager import ResearchClientManager
from functools import wraps
import asyncio
import os

from time import perf_counter
from flask import current_app



USE_PUBMED = os.getenv("USE_PUBMED", "0") == "1"
if USE_PUBMED:
    from src.clients.pubmed_client import PubMedClient

api = Blueprint('api', __name__)
def _sources_block(docs):
    """Build a numbered list matching your citation cards."""
    lines = []
    for i, d in enumerate(docs, 1):
        title = (d.get("title") or "").strip()
        first_author = (d.get("authors") or ["Unknown"])[0]
        journal = d.get("journal") or ""
        year = d.get("year") or ""
        lines.append(f"[{i}] {title} — {first_author}. {journal} {year}.")
    return "\n".join(lines)

def _make_detailed_answer(openai_client, question, sources_block):
    """Ask the LLM for paragraphs with bracketed numeric cites."""
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    prompt = f"""Using ONLY the numbered sources below, write 2–4 cohesive paragraphs that answer the question.
Insert bracketed numeric citations like [2] immediately after the facts they support. No bullets, no lists.
State uncertainties if evidence is indirect or mixed.

Question: {question}

Sources:
{sources_block}
"""
    r = openai_client.chat.completions.create(
        model=model,
        temperature=0.2,
        messages=[{"role":"user","content": prompt}],
    )
    return r.choices[0].message.content.strip()
# Initialize clients
#pubmed_client = PubMedClient()
pubmed_client = PubMedClient() if USE_PUBMED else None
db_manager = DatabaseManager(config.DATABASE_URL)
llm_client = LLMClient()
semantic_client = SemanticScholarClient()
client_manager = ResearchClientManager()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def async_route(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(f(*args, **kwargs))
        finally:
            loop.close()
    return wrapper

async def call_llm_api(prompt: str) -> str:
    """Call the LLM API with the given prompt."""
    try:
        response = await llm_client.analyze_papers(prompt)
        return response
    except Exception as e:
        logger.error(f"LLM API error: {str(e)}")
        return f"Error generating analysis: {str(e)}"

@api.route('/research_question', methods=['POST'])
@async_route
async def research_question():
    data = request.json
    if not data or 'question' not in data:
        return jsonify({'error': 'No question provided'}), 400

    try:
        # First get papers
        papers = await client_manager.search_all(data['question'])
        
        print("\n=== Papers being sent to LLM ===")
        for i, paper in enumerate(papers, 1):
            print(f"\nPaper {i}:")
            print(f"Title: {paper.get('title')}")
            print(f"Source: {paper.get('source')}")
        
        # Create LLM client and analyze
        llm_client = LLMClient()
        analysis = llm_client.analyze_papers(papers, data['question'])
        
        print("\n=== Analysis completed ===")
        print("First 100 chars of analysis:", analysis[:100])
        
        response_data = {
            'analysis': analysis,
            'papers': papers
        }
        
        print("\n=== Papers in response ===")
        for i, paper in enumerate(papers, 1):
            print(f"\nPaper {i}:")
            print(f"Title: {paper.get('title')}")
            print(f"Source: {paper.get('source')}")
        
        return jsonify(response_data)

    except Exception as e:
        print(f"Research question error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api.route('/search', methods=['GET'])
@async_route
async def search():
    query = request.args.get('query')
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    
    try:
        results = await client_manager.search_all(query)
        return jsonify({'papers': results})
    except Exception as e:
        print(f"Search error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api.route('/paper/<source>/<paper_id>', methods=['GET'])
@async_route
async def get_paper(source, paper_id):
    try:
        paper = await client_manager.get_paper_details(paper_id, source)
        return jsonify(paper)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        print(f"Paper detail error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Add a basic health check route
@api.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200


