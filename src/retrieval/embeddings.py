from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_core.embeddings import Embeddings

load_dotenv()


try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    SentenceTransformer = None
    HAS_SENTENCE_TRANSFORMERS = False


@lru_cache(maxsize=4)
def _load_sentence_transformer(model_name: str):
    if not HAS_SENTENCE_TRANSFORMERS:
        raise ImportError("sentence_transformers is not installed.")
    return SentenceTransformer(model_name)


class MiniLMEmbeddings(Embeddings):
    """Embedding wrapper that supports:
    1. Local SentenceTransformer (all-MiniLM-L6-v2) if installed.
    2. Google Generative AI Embeddings (models/text-embedding-004) if sentence-transformers
       is not installed, or if EMBEDDING_PROVIDER=google or model_name starts with 'models/'.
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2", google_api_key: str | None = None):
        self.model_name = model_name
        self.google_api_key = google_api_key or os.getenv("GOOGLE_API_KEY")

        provider = os.getenv("EMBEDDING_PROVIDER", "").lower()
        use_google = (
            provider in {"google", "gemini"}
            or model_name.startswith("models/")
            or not HAS_SENTENCE_TRANSFORMERS
        )

        if use_google:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings

            google_model = model_name if model_name.startswith("models/") else "models/gemini-embedding-001"
            self._backend = GoogleGenerativeAIEmbeddings(
                model=google_model,
                google_api_key=self.google_api_key,
            )
            self._mode = "google"
        else:
            self._backend = _load_sentence_transformer(model_name)
            self._mode = "sentence_transformers"

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self._mode == "google":
            return self._backend.embed_documents(texts)
        embeddings = self._backend.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        if self._mode == "google":
            return self._backend.embed_query(text)
        embedding = self._backend.encode([text], normalize_embeddings=True)
        return embedding[0].tolist()

