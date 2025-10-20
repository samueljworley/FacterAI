# src/app/services/planner.py
import re
from typing import Dict, List

CONNECTORS = r"(?:affect|effects?|impact|influence|association|relationship|link|increase|decrease|change|vs|on|in)"

def _tokens(s: str) -> List[str]:
    # very light tokenization; no new deps
    return [t for t in re.split(r"[^a-zA-Z0-9]+", s.lower()) if len(t) > 2]

def _split_query(q: str):
    # try to split around a connector word to get A and B
    m = re.split(CONNECTORS, q, maxsplit=1, flags=re.IGNORECASE)
    if len(m) == 2:
        left, right = m[0], m[1]
        return _tokens(left), _tokens(right)
    # fallback: just use all tokens for both
    toks = _tokens(q)
    return toks, toks

def plan_query(query: str) -> Dict:
    a, b = _split_query(query)

    # Buckets the “planner” wants the Fetcher to retrieve
    return {
        "raw_query": query,
        "buckets": {
            "joint": {
                "intent": "papers that mention BOTH sides together",
                "must": a[:5] + b[:5],  # cheap heuristic
                "should": [f"{a[0]} {b[0]}"] if a and b else [],
            },
            "topic_a_context": {
                "intent": "Thing A in hormone/biomarker context",
                "must": a[:6],
                "should": ["hormone", "testosterone", "androgen", "endocrine", "acute", "long-term"],
            },
            "topic_b_context": {
                "intent": "Thing B in exposure/intervention context",
                "must": b[:6],
                "should": ["exercise", "training", "resistance", "strength", "aerobic", "intervention"],
            },
            "modifiers": {
                "intent": "common moderators to check (NOT hardcoded to any single topic)",
                "should": ["age", "adiposity", "bmi", "sleep", "duration", "intensity", "sex", "dose", "baseline"],
            }
        }
    }
