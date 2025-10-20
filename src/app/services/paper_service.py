from typing import List, Dict, Tuple, Any
import sys
from datetime import datetime
#from src.clients import pubmed_client, europepmc_client, arxiv_client
from .impact_service import ImpactService
from .cache_service import CacheService
from .arxiv_metrics import ArxivMetrics
from src.clients.pubmed_client import PubMedClient
import numpy as np
import faiss
import time
#from src.app.services.db_service import DBService
#from db.dynamodb_handler import DynamoDBHandler
from db.paper_processor import PaperProcessor
from db.vector_store import VectorStore
from db.reranker import SearchReranker
import logging
import re
import aiohttp

import asyncio
from src.clients.semantic_scholar import SemanticScholarClient
import hashlib

import httpx
import logging
from src.core.model_cache import ModelCache
import numpy as np  # if you use encode() results numerically
import os
USE_PUBMED = os.getenv("USE_PUBMED", "0") == "1"
if USE_PUBMED:
    from src.clients.pubmed_client import PubMedClient




logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


class Paper:
    def __init__(self, title: str, authors: List[str], abstract: str, doi: str, 
                 date: datetime, journal: str, impact_factor: float = 0.0):
        self.title = title
        self.authors = authors
        self.abstract = abstract
        self.doi = doi
        self.date = date
        self.journal = journal
        self.impact_factor = impact_factor

class PaperService:
    def __init__(self):
        self.pubmed = PubMedClient() if USE_PUBMED else None
        #self.europepmc = europepmc_client
        #self.arxiv = arxiv_client
        self.cache = CacheService()
        self.impact_service = ImpactService()
        self.arxiv_metrics = ArxivMetrics()
        self.model_cache = ModelCache()
        self.encoder = self.model_cache.get_sentence_transformer()  # may be None when USE_EMBED=0
        self.index = None
        self.papers = []
        self.min_papers = 2
        self.max_papers = 6
        self.rate_limit_delay = 0.34  # Delay between requests to avoid rate limits
        #DBHandler()
        self.processor = PaperProcessor()
        self.vector_store = VectorStore()
        self.reranker = SearchReranker()
        self.semantic_scholar = SemanticScholarClient()
        logger.debug("PaperService initialized")
        self.lambda_url = os.getenv("LAMBDA_SEARCH_URL", "https://la6uumnjdhl5xawcst6uqthqfa0urvfx.lambda-url.us-west-1.on.aws/")
        logger.info(f"[PaperService] LAMBDA_SEARCH_URL = {self.lambda_url}")
        
    QUESTION_STOPWORDS = {
            "how","what","why","when","where","which","who","whom","whose",
            "does","do","did","is","are","was","were","be","being","been",
            "affect","effects","impact","impacts",
            "increase","increases","decrease","decreases","change","changes",
            "cause","causes","lead","leads","improve","improves","reduce","reduces",
            "on","of","to","in","for","with","by","the","a","an"
}

    def _clean_for_lexical(self, q: str) -> str:
        # keep quoted phrases intact; drop QA glue-words; keep tokens >2 chars
        tokens = re.findall(r'\".*?\"|\w+', q.lower())
        keep = []
        for t in tokens:
            if t.startswith('"'):
                keep.append(t)
            elif t.isalnum() and t not in self.QUESTION_STOPWORDS and len(t) > 2:
                keep.append(t)
        return " ".join(keep) or q

    def _extract_ab(self, query: str):
        """
        Pull 'A' and 'B' from comparative queries like:
        - "metformin vs sulfonylurea for A1c reduction"
        - "compare metformin and sulfonylurea"
        - "metformin versus sulfonylureas"
        Returns (A, B) or (None, None).
        """
        q = (query or "").lower().strip()
        if not q:
            return (None, None)

        # normalize common connectors
        q = re.sub(r'\bversus\b', 'vs', q)

        # Prefer 'A vs B ...' pattern, ignore trailing "for/to ..." clause
        m = re.search(r'\b(.+?)\s+vs\.?\s+(.+?)(?:\s+(?:for|to)\b|$)', q)
        if m:
            A = m.group(1).strip(' ,.?')
            B = m.group(2).strip(' ,.?')
            return (A, B)

        # Also accept "compare A and/with B ..."
        m = re.search(r'\bcompare\s+(.+?)\s+(?:and|with)\s+(.+?)(?:\s+(?:for|to)\b|$)', q)
        if m:
            A = m.group(1).strip(' ,.?')
            B = m.group(2).strip(' ,.?')
            return (A, B)

        return (None, None)


    def _comparative_boost(self, paper: dict, A: str, B: str) -> float:
        """
        Generic, topic-agnostic: +1 if both A and B appear in title/abstract (case-insensitive).
        No synonym lists, no domain rules.
        """
        title = (paper.get("title") or "").lower()
        abstract = (paper.get("abstract") or "").lower()
        txt = f"{title} {abstract}"
        a_hit = A.lower() in txt
        b_hit = B.lower() in txt
        return 1.0 if (a_hit and b_hit) else 0.0


    async def _search_with_lambda(self, query: str, size: int = 24):
        url = self.lambda_url
        if not url:
            print("[Lambda] LAMBDA_SEARCH_URL not set; skipping OpenSearch path")
            return []
        try:
            print(f"[Lambda →] GET {url} q={query!r} size={size}")
            import httpx, json
            async with httpx.AsyncClient(timeout=httpx.Timeout(12.0, connect=5.0)) as client:
                r = await client.get(url, params={"q": query, "size": size})
                r.raise_for_status()
                data = r.json()
            hits = data.get("hits") or []
            total = (data.get("total") or {}).get("value") if isinstance(data.get("total"), dict) else data.get("total")
            print(f"[Lambda ←] total={total} hits={len(hits)} index={data.get('index')}")
            return hits
        except Exception as e:
            print(f"[Lambda ✖] {type(e).__name__}: {e}")
            return []




    def calculate_paper_score(self, paper: Paper) -> float:
        """Calculate overall paper score for ranking"""
        # Base score from impact factor
        score = paper.impact_factor * 0.4  # 40% weight

        # Recency score (newer papers get higher score)
        days_old = (datetime.now() - paper.date).days
        recency_score = max(0, 1 - (days_old / 365)) * 0.3  # 30% weight

        # Source quality score
        if paper.journal.lower().startswith('arxiv'):
            category = paper.journal.split(':')[1]
            source_score = self.arxiv_metrics.get_paper_weight(category) * 0.2  # 20% weight
        else:
            source_score = min(1.0, paper.impact_factor / 10) * 0.2

        # Citation score
        citation_score = min(1.0, paper.citations / 100) * 0.1  # 10% weight

        return score + recency_score + source_score + citation_score

    def _format_pubmed_query(self, query: str) -> str:
        """Format the user query for PubMed search"""
        logger.debug(f"Original query: {query}")
        
        # Basic cleaning
        query = query.lower()
        query = re.sub(r'\?|\.|\,', '', query)
        
        # Much more minimal stop words - only remove the most common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must', 'shall'}
        
        # Split into words and keep meaningful terms
        terms = [word for word in query.split() if word not in stop_words and len(word) > 2]
        
        # If we have too few terms, be even less restrictive
        if len(terms) < 2:
            # Only remove the most basic words
            basic_stop_words = {'the', 'a', 'an', 'and', 'or', 'but'}
            terms = [word for word in query.split() if word not in basic_stop_words and len(word) > 2]
        
        # If still too few terms, use the original query with minimal cleaning
        if len(terms) < 2:
            terms = [word for word in query.split() if len(word) > 1]  # Allow 2-letter words
        
        # Use OR instead of AND for broader matching
        formatted_terms = []
        for term in terms:
            formatted_terms.append(f"{term}[Title/Abstract]")
        
        # Join terms with OR for broader results
        formatted_query = " OR ".join(formatted_terms)
        
        logger.debug(f"Formatted PubMed query: {formatted_query}")
        return formatted_query

    # inside src/app/services/paper_service.py

    async def search_papers(self, query: str, query_type: str) -> List[Dict[str, Any]]:
        print(f"[search_papers] query={query!r} type={query_type}")
        """
        Biomed-only retrieval:
        - call OpenSearch via Lambda once
        - normalize, dedupe, single rerank
        - return top N (self.max_papers)
        """
        try:
            # 1) Fetch from your Lambda/OpenSearch (bigger size for rerank headroom)
            size = max(self.max_papers * 3, 48)
            os_papers: List[Dict[str, Any]] = await self._search_with_lambda(query, size=size)

            # 2) Normalize minimal fields we actually use downstream
            papers: List[Dict[str, Any]] = []
            for p in (os_papers or []):
                papers.append({
                    "pmid": p.get("pmid"),
                    "title": p.get("title") or "Untitled",
                    "journal": p.get("journal") or "",
                    "publication_date": str(p.get("publication_date") or p.get("year") or ""),
                    # prefer abstract; fall back to text_for_rerank so UI always has something
                    "abstract": p.get("abstract") or p.get("text_for_rerank") or "",
                    "url": p.get("url") or "",
                    "source": "opensearch",
                })

            # 3) Dedupe by stable id (pmid → doi/url → title tuple)
            seen = set()
            uniq: List[Dict[str, Any]] = []
            for p in papers:
                key = (
                    p.get("pmid")
                    or p.get("doi")
                    or p.get("url")
                    or f"{p.get('title','')}::{p.get('journal','')}::{p.get('publication_date','')}"
                )
                if key in seen:
                    continue
                seen.add(key)
                uniq.append(p)

            # 4) Single rerank + cap to max_papers
            if uniq:
                uniq = self.reranker.rerank_results(query, uniq, self.max_papers)

            # >>> STEP 2: comparative boost (topic-agnostic) >>>
            A, B = self._extract_ab(query)
            if A and B and uniq:
                # annotate each paper with a simple co-mention boost
                for p in uniq:
                    p["_comparative_boost"] = self._comparative_boost(p, A, B)

                # combine with existing rerank_score if present
                def _combined_score(p):
                    base = p.get("rerank_score")
                    try:
                        base = float(base)
                    except (TypeError, ValueError):
                        base = 0.0
                    return base + 2.0 * p.get("_comparative_boost", 0.0)  # modest weight

                uniq.sort(key=_combined_score, reverse=True)
            # <<< STEP 2 <<<

            return uniq[:self.max_papers]



        except Exception as e:
            logger.error(f"Error in search_papers (biomed-only): {str(e)}")
            return []


    async def _search_research(self, query: str) -> List[Dict[str, Any]]:
        """Search research papers using async clients"""
        try:
            # Search PubMed
            pubmed_results = await self.pubmed.search(
                query=query,
                max_results=self.max_papers
            )
            
            print(f"Found {len(pubmed_results)} papers from PubMed")
            return pubmed_results

        except Exception as e:
            print(f"Error in _search_research: {str(e)}")
            return []

    

    def format_citation(self, paper: Paper) -> str:
        """Format paper citation in a standard way"""
        authors_text = ", ".join(paper.authors[:3])
        if len(paper.authors) > 3:
            authors_text += " et al."
            
        year = paper.date.year if isinstance(paper.date, datetime) else "N/A"
        
        return f"{paper.title} ({year}). {authors_text}. {paper.journal}. DOI: {paper.doi}"

    def _format_pubmed_papers(self, results) -> List[Paper]:
        papers = []
        for result in results:
            journal = result.get('journal', '')
            impact_factor = self.impact_service.get_impact_factor(journal)
            
            papers.append(Paper(
                title=result.get('title'),
                authors=result.get('authors', []),
                abstract=result.get('abstract'),
                doi=result.get('doi'),
                date=result.get('publication_date'),
                journal=journal,
                impact_factor=impact_factor
            ))
        return sorted(papers, 
                     key=lambda p: (p.impact_factor, p.date), 
                     reverse=True)

    

    async def _get_citation_count(self, pmid: str) -> int:
        """Get citation count from Semantic Scholar API"""
        try:
            return await self.semantic_scholar.get_citation_count(pmid)
        except Exception as e:
            logger.error(f"Error getting citation count for {pmid}: {str(e)}")
            return 0

    async def _process_paper(self, pmid: str) -> Dict[str, Any]:
        """Process a single paper through the pipeline"""
        logger.info(f"Processing paper {pmid}")
        try:
            # Check existing paper
            existing_paper = self.db.get_paper(
                document_id=pmid,
                category='pubmed'
            )
            
            if existing_paper:
                logger.info(f"Found existing paper {pmid}")
                return existing_paper

            # Fetch new paper
            logger.info(f"Fetching new paper {pmid}")
            paper_data = self.pubmed.fetch_paper_details(pmid) if USE_PUBMED else None
            
            # Get citation count
            citation_count = await self.semantic_scholar.get_citation_count(pmid)
            paper_data['citation_count'] = citation_count
            
            # Process text
            text = f"{paper_data['title']} {paper_data['abstract']}"
            text_hash = hashlib.sha256(text.encode()).hexdigest()
            
            # Store in DynamoDB
            logger.info(f"Storing paper {pmid} in DynamoDB")
            self.db.insert_paper(
                document_id=pmid,
                category='pubmed',
                title=paper_data['title'],
                authors=paper_data['authors'],
                publication_date=paper_data['publication_date'],
                journal=paper_data['journal'],
                abstract=paper_data['abstract'],
                citation_count=citation_count,
                categories=['research'],
                keywords=paper_data.get('keywords', []),
                full_text_hash=text_hash
            )
            
            
            return paper_data
    

        except Exception as e:
            logger.error(f"Error processing paper {pmid}: {str(e)}")
            return None 