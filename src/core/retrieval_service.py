"""
RetrievalService: Handles retrieval and chunk formatting
"""
import time
from typing import List, Dict, Any
from .response_context import Chunk, ResponseContext, context_manager
from src.app.services.paper_service import PaperService

# ✅ FAISS is already in your repo; use the cached service you have
# (paths from your grep output)
from src.core.cached_faiss_retrieval_service import CachedFAISSRetrievalService

class RetrievalService:
    """Service for retrieving and formatting research papers"""

    def __init__(self):
        self.paper_service = PaperService()
        self.faiss_service = CachedFAISSRetrievalService()
        self.max_chunks = 12
        # if OS returns fewer than this, augment with FAISS
        self.min_candidates_for_rerank = 24

    async def retrieve(self, query: str, size: int = 20) -> ResponseContext:
        """
        Retrieve papers and create response context
        Returns: ResponseContext with selected_chunks
        """
        start_time = time.time()

        try:
            # 1) Primary lexical retrieval via your Lambda/OpenSearch
            papers: List[Dict[str, Any]] = await self.paper_service.search_papers(query, "research")

            # 2) If too few, augment with FAISS (semantic fallback)
            if len(papers) < self.min_candidates_for_rerank:
                try:
                    faiss_papers = self.faiss_service.search_with_faiss(query, size=max(size * 3, 48))
                except Exception as e:
                    print(f"[retrieval] FAISS fallback error: {e}")
                    faiss_papers = []

                if faiss_papers:
                    papers = self._dedupe_papers(papers + faiss_papers)

            # 3) Convert to chunks expected downstream and cap to max_chunks
            selected_chunks = self._convert_papers_to_chunks(papers)[: self.max_chunks]

            retrieval_latency = (time.time() - start_time) * 1000.0

            # 4) Create response context
            context = context_manager.create_context(
                query=query,
                selected_chunks=selected_chunks,
                retrieval_latency_ms=retrieval_latency,
            )
            return context

        except Exception as e:
            raise RuntimeError(f"Retrieval failed: {str(e)}")

    # ----------------------- helpers -----------------------

    def _dedupe_papers(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate OS + FAISS candidates by stable identifiers."""
        seen = set()
        out: List[Dict[str, Any]] = []
        for p in papers:
            key = (
                p.get("pmid")
                or p.get("arxiv_id")
                or p.get("doi")
                or p.get("url")
                or p.get("id")
                or p.get("title")
            )
            if not key:
                # last-resort guard to avoid dropping valid but keyless items
                key = hash((p.get("title"), p.get("journal"), p.get("year")))
            if key in seen:
                continue
            seen.add(key)
            out.append(p)
        return out

    def _convert_papers_to_chunks(self, papers: List[Dict[str, Any]]) -> List[Chunk]:
        """Convert paper data to Chunk objects."""
        chunks: List[Chunk] = []

        for i, paper in enumerate(papers):
            try:
                title = paper.get("title") or "Untitled"
                # Prefer abstract; fall back to any text the retriever provided
                abstract = (
                    paper.get("abstract")
                    or paper.get("text_for_rerank")
                    or paper.get("summary")
                    or paper.get("full_text")
                    or paper.get("text")
                    or ""
                )
                pmid = paper.get("pmid") or ""
                arxiv_id = paper.get("arxiv_id") or ""
                # You were not using year/journal in Chunk, but keep them if you later display metadata
                # year = paper.get("year") or paper.get("publication_date") or ""
                # journal = paper.get("journal") or ""

                identifier = pmid or arxiv_id or paper.get("doi") or paper.get("url") or f"paper_{i}"

                chunk = Chunk(
                    id=str(i + 1),
                    title=title,
                    pmid_or_doi=identifier,
                    section="Abstract",
                    text=abstract,
                )
                chunks.append(chunk)

            except Exception as e:
                print(f"[retrieval] Error converting paper {i} to chunk: {e}")
                continue

        return chunks


# Global instance
retrieval_service = RetrievalService()
