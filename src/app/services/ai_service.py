# src/app/services/ai_service.py
from __future__ import annotations

import os
import re
import asyncio
from typing import List, Dict, Any, Optional

from openai import OpenAI
from src.app.services.paper_service import PaperService


class AIService:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # Keep your current default; you can override with OPENAI_MODEL env var
        self.model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        self.paper_service = PaperService()

    # ---------------- public APIs ----------------
    def classify_query_type(self, question: str) -> str:
        """
        Map a natural-language question to one of:
        'comparative' | 'diagnosis' | 'test_accuracy' | 'prognosis' | 'research' (default)
        """
        if not question:
            return "research"

        text = question.lower()

        # 1) Test accuracy / diagnostic performance cues
        if re.search(r'\b(sensitivity|specificity|likelihood ratio|lr\+|lr-|roc|auc|cut[\s-]?off|threshold|ppv|npv|diagnostic accuracy|screening test)\b', text):
            return "test_accuracy"

        # 2) Comparative / head-to-head cues
        if re.search(r'\b(vs\.?|versus|compared to|compare|comparison|better than|superior|non[- ]?inferior)\b', text):
            return "comparative"

        # 3) Diagnosis / differential cues
        if re.search(r'\b(differential|ddx|diagnos(e|is)|work[- ]?up|causes? of|what could cause|etiolog(y|ies))\b', text):
            return "diagnosis"

        # 4) Prognosis / risk cues
        if re.search(r'\b(prognos(?:is|tic)|risk of|chance of|probabilit|mortality|survival|outcome[s]?|hazard|incidence|over time)\b', text):
            return "prognosis"

        # 5) Generic exposure→outcome phrasing (e.g., "how does X affect Y")
        if re.search(r'\b(how|does|affect|impact|increase|decrease|association|effect)\b', text):
            # If risk-ish outcomes are mentioned, lean prognosis; else treat as general research synthesis
            if re.search(r'\b(risk|mortality|survival|incidence|outcome[s]?)\b', text):
                return "prognosis"
            return "research"

        # Fallback
        return "research"
    
    async def process_query(
        self,
        query: str,
        query_type: str = "research",
        papers: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Legacy pipeline: formats provided papers and asks the model to answer.
        Kept for callsites that still use it.
        """
        papers = papers or []
        papers_context = self._format_papers_context(papers)

        prompt = (
            f"Based on the following research papers:\n\n"
            f"{papers_context if papers_context else 'No scientific papers found.'}\n\n"
            f"Please answer this question:\n{query}\n\n"
            "Provide a comprehensive answer that:\n"
            "1. Directly addresses the question\n"
            "2. Cites specific findings from the papers using professional academic citation "
            "   format (e.g., [Author et al., Year] or [Journal, Year])\n"
            "3. Notes any limitations or uncertainties\n"
            "Do not include the references list in your response — they will be displayed separately."
        )

        def _call():
            return self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.get_system_prompt(query_type)},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )

        try:
            response = await asyncio.to_thread(_call)
            answer = (response.choices[0].message.content or "").strip()
            return {
                "result": {
                    "answer": answer,
                    "sources": self._format_sources_for_sidebar(papers),
                },
                "status": "success",
            }
        except Exception as e:
            return {
                "result": {
                    "answer": f"Error processing your query: {str(e)}",
                    "sources": [],
                },
                "status": "error",
                "error": str(e),
            }
        
    async def rewrite_query(self, query: str) -> str:
        """
        Rewrite a user question into a compact, recall-friendly boolean-ish query
        with synonyms and medical phrasing. Keeps it short to remain compatible
        with OpenSearch/FAISS. General-purpose (no hardcoded topics).
        """
        system = (
            "You rewrite user research questions into concise search strings for "
            "scientific/medical retrieval. Use key concepts with synonyms connected "
            "by AND/OR and parentheses. Prefer human/population terms if implied. "
            "Keep it under ~12 tokens. No quotes. No punctuation other than AND/OR/()."
        )
        user = f"Rewrite this into a boolean-ish search string: {query}"

        try:
            resp = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.2,
            )
            text = (resp.choices[0].message.content or "").strip()
            # very light sanity check; fall back if it looks empty
            return text if len(text.split()) >= 2 else query
        except Exception:
            # on any failure, just return original
            return query

    async def summarize_citations(
        self,
        query: str,
        citations: List[Dict[str, Any]],
        *,
        max_papers: int = 8,
    ) -> str:
        """
        Produce a short, source-grounded summary from retrieved citations.
        Returns an empty string on failure.
        """
        if not citations:
            return ""

        def _mk_line(p: Dict[str, Any], idx: int) -> str:
            title = (p.get("title") or "Untitled").strip()
            journal = (p.get("journal") or "N/A").strip()
            pub = (p.get("publication_date") or "").strip()
            year = pub.split("-")[0] if pub else ""
            abstract = (p.get("abstract") or "").strip()
            if abstract:
                abstract = abstract[:600] + ("…" if len(abstract) > 600 else "")
            return f"[{idx}] {title} — {journal} ({year})\nAbstract: {abstract}"

        context = "\n\n".join(
            _mk_line(p, i) for i, p in enumerate(citations[:max_papers], start=1)
        )

        sys_prompt = (
            "You are a scientific research assistant. Using only the papers provided, "
            "write a concise, neutral summary that answers the user's question. "
            "Reference papers inline as [1], [2], etc., matching the numbering. "
            "Highlight study design (e.g., RCT, cohort, meta-analysis), population, "
            "direction/magnitude of effects, and key caveats. Do not fabricate sources."
        )

        user_prompt = (
            f"Question: {query}\n\nPapers:\n{context}\n\n"
            "Write 4–8 bullet points followed by a one-sentence bottom line."
        )

        def _call():
            return self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            )

        try:
            resp = await asyncio.to_thread(_call)
            return (resp.choices[0].message.content or "").strip()
        except Exception:
            return ""

    def extract_doi_from_text(self, text: str) -> List[str]:
        """Extract DOIs from text using regex."""
        doi_pattern = r"https?://doi\.org/([^/\s]+)"
        return re.findall(doi_pattern, text or "")

    def validate_query(self, query: str) -> bool:
        if not query or len(query.strip()) < 3:
            return False
        return True

    # ---------------- helpers ----------------

    def _format_papers_context(self, papers: List[Dict[str, Any]]) -> str:
        if not papers:
            return "No relevant papers found."
        blocks: List[str] = []
        for i, paper in enumerate(papers, start=1):
            pub = (paper.get("publication_date") or "").strip()
            year = pub.split("-")[0] if pub else ""
            authors = paper.get("authors") or []
            if isinstance(authors, list):
                if len(authors) == 0:
                    author_cite = "N/A"
                elif len(authors) == 1:
                    author_cite = authors[0]
                elif len(authors) == 2:
                    author_cite = f"{authors[0]} and {authors[1]}"
                else:
                    author_cite = f"{authors[0]} et al."
            else:
                author_cite = str(authors)

            title = paper.get("title") or "Untitled"
            journal = paper.get("journal") or "N/A"
            abstract = (paper.get("abstract") or "").strip()

            blocks.append(
                f"{i}. {author_cite} ({year}). {title}. {journal}.\nAbstract: {abstract}"
            )
        return "\n\n".join(blocks)

    def _format_sources_for_sidebar(
        self, papers: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        formatted: List[Dict[str, Any]] = []
        for p in papers:
            pmid = p.get("pmid") or p.get("document_id") or ""
            formatted.append(
                {
                    "title": p.get("title") or "",
                    "authors": p.get("authors") or [],
                    "journal": p.get("journal") or "",
                    "pmid": pmid,
                    "abstract": p.get("abstract") or "",
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
                    "year": (p.get("publication_date") or "").split("-")[0]
                    if p.get("publication_date")
                    else "",
                }
            )
        return formatted

    def get_sources_by_type(self, query_type: str) -> List[str]:
        source_priorities = {
            "research": ["pubmed", "europepmc", "arxiv"],
            "solution_based": ["wolfram", "arxiv", "scholarpedia"],
            "concept": ["wikipedia", "scholarpedia", "stanford_encyclopedia"],
            "coding": ["github", "stackoverflow", "documentation"],
        }
        return source_priorities.get(query_type, [])

    def get_system_prompt(self, query_type: str) -> str:
        PROMPTS = {
            "comparative": """You are a comparative-effectiveness analyst. Use ONLY the papers provided below.
            Write a clear answer that compares the interventions/exposures in the user’s question for the specified outcomes.

            Do:
            - Start with a one-sentence bottom line (who, what, outcome).
            - Summarize the best head-to-head evidence first; if none, state that evidence is indirect and compare via common comparators.
            - Report effect sizes with units and direction (e.g., RR, OR, MD) and, when possible, absolute differences and NNT/NNH.
            - Note population, setting, and typical dose/duration if relevant.
            - Call out important subgroup effects, heterogeneity, and key harms.
            - End with a practical takeaway (“Most benefit is seen in …; avoid in …”).

            Citations:
            - Use bracketed numbers [1], [2] tied to the provided paper list.
            - If evidence is weak/observational, say so.

            Do NOT:
            - Invent studies or numbers. If data are insufficient or conflicting, say that plainly.

            {papers_context}
            """,
            "diagnosis": """You are a clinician building a differential diagnosis. Use ONLY the papers provided below.

            Task:
            - Give a ranked Top 5 differential for the user’s presentation.
            - For each item: 1 key discriminator (history/exam/lab/imaging), 1 supporting ‘why’, and 1 “rule-out next” test.
            - List red-flag features that require urgent action.
            - Provide an initial workup plan (first-line tests) and when specialist referral is warranted.
            - Keep it concise (≤10 bullets total), factual, and tied to evidence.

            Citations:
            - Use bracketed numbers [#] after bullets when evidence supports that point.

            Do NOT give a definitive diagnosis; focus on probabilities and next steps.

            {papers_context}
            """,
            "test_accuracy": """You are a diagnostics methodologist. Use ONLY the papers provided below.

            Task:
            - Report sensitivity, specificity, LR+, LR−, and any recommended thresholds.
            - If multiple studies, give a reasonable range and the best pooled/representative estimate.
            - Briefly note sources of bias (spectrum, verification) and study setting/population.
            - Explain that PPV/NPV depend on prevalence; give an example post-test probability using a plausible pretest probability for the target setting.
            - One-paragraph takeaway: when the test meaningfully rules-in or rules-out.

            Citations:
            - Use bracketed numbers [#] for each key number.

            If data are inconsistent or low quality, state the limitation.

            {papers_context}
            """,
            "prognosis": """You are a prognostic evidence reviewer. Use ONLY the papers provided below.

            Task:
            - Summarize absolute risks over relevant time horizons (e.g., 30-day, 1-year), per 1,000 people when possible.
            - Include hazard ratios/relative risks and any risk modifiers (age, comorbidity, severity).
            - Mention model performance if applicable (C-statistic/AUC, calibration).
            - Name validated risk scores or calculators and when to use them.
            - End with a clear bottom line about expected outcomes and key modifiers.

            Citations:
            - Use bracketed numbers [#] to anchor numbers to studies.

            Avoid speculation beyond the provided evidence.

            {papers_context}
            """,
                        # fallback for your current mode
            "research": """You are a scientific research assistant... (your existing default)"""
        }
        return PROMPTS.get(query_type, PROMPTS["research"])


    def extract_sources(self, content: str) -> List[str]:
        # Placeholder for future source extraction
        return []
