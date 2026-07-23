"""
RAG (Retrieval-Augmented Generation) package.

Provides:
  - RAGService: Core ingestion and legacy retrieval
  - AdvancedRetriever: Full pipeline (expansion → hybrid → rerank)
  - RetrievalConfig: Pipeline configuration

Backward-compatible: `from app.services.rag import RAGService` still works.
"""

from app.services.rag.service import RAGService
from app.services.rag.retriever import AdvancedRetriever, RetrievalConfig

__all__ = [
    "RAGService",
    "AdvancedRetriever",
    "RetrievalConfig",
]
