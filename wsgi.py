# If your factory function lives in app.py at the project root:
# wsgi.py
import os, sys, types
print("WSGI START:", os.getenv("APP_VERSION","?"), flush=True)

# Hard-disable PubMed if the flag is off (your default)
if os.getenv("USE_PUBMED", "0") != "1":
    # Stub for src.clients.pubmed_client.PubMedClient
    m1 = types.ModuleType("src.clients.pubmed_client")
    class _NoPubMedClient:
        def __init__(self, *a, **k):
            raise RuntimeError("PubMed disabled")
    m1.PubMedClient = _NoPubMedClient
    sys.modules["src.clients.pubmed_client"] = m1

    # Stub for src.data_collection.pubmed_client.PubMedClient (some files import from here)
    m2 = types.ModuleType("src.data_collection.pubmed_client")
    m2.PubMedClient = _NoPubMedClient
    sys.modules["src.data_collection.pubmed_client"] = m2

    # Stub for src.embeddings.fetch_pubmed.PubMedFetcher
    m3 = types.ModuleType("src.embeddings.fetch_pubmed")
    class _NoPubMedFetcher:
        def __init__(self, *a, **k):
            raise RuntimeError("PubMed disabled")
    m3.PubMedFetcher = _NoPubMedFetcher
    sys.modules["src.embeddings.fetch_pubmed"] = m3

from app import create_app  # keep this AFTER the stubs
app = create_app()


