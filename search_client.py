# search_client.py
import os
import requests

LAMBDA_URL = (
    os.getenv("LAMBDA_SEARCH_URL")
    or os.getenv("NEXT_PUBLIC_SEARCH_URL")
    or os.getenv("VITE_SEARCH_URL")
)

def query(q: str, size: int = 10):
    if not LAMBDA_URL:
        raise RuntimeError("LAMBDA_SEARCH_URL (or NEXT_PUBLIC_SEARCH_URL) is not set")
    params = {"q": q, "size": size}
    r = requests.get(LAMBDA_URL, params=params, timeout=10)
    r.raise_for_status()
    return r.json()
