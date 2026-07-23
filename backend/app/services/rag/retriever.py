"""
Advanced Retriever — Pipeline orchestrator for the full RAG retrieval flow.

Wires together:
  1. Query Expansion → generates alternative search queries
  2. Hybrid Search → BM25 + pgvector for each query, RRF fusion
  3. Cross-Encoder Reranking → scores all candidates, returns top-k
  4. Parent Resolution → if a matched chunk has a parent_id, returns parent text

This replaces the simple cosine-similarity retrieve() in the original RAGService.
"""

import asyncio
import time
from dataclasses import dataclass, field

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.rag.hybrid_search import HybridSearchRetriever
from app.services.rag.reranker import ChunkReranker
from app.services.rag.query_expansion import QueryExpander

log = structlog.get_logger()


@dataclass
class RetrievalConfig:
    """Configuration for the advanced retrieval pipeline."""
    enable_expansion: bool = True
    enable_reranking: bool = True
    hybrid_top_k: int = 8           # candidates before reranking
    final_top_k: int = 4            # chunks sent to LLM
    rrf_weight_bm25: float = 0.4
    rrf_weight_vector: float = 0.6


class AdvancedRetriever:
    """
    Top-level retrieval orchestrator.

    Pipeline:
      Query → [Expansion] → Hybrid Search (BM25+Vector, RRF) →
      [Reranking] → Parent Resolution → Formatted Context

    Returns the same format as RAGService.retrieve() (a formatted string)
    so it's a drop-in replacement in websocket.py.
    """

    def __init__(
        self,
        db: AsyncSession,
        redis=None,
        embed_fn=None,
        config: RetrievalConfig | None = None,
    ) -> None:
        self.db = db
        self.redis = redis
        self.embed_fn = embed_fn  # async callable: list[str] -> list[list[float]]
        self.config = config or RetrievalConfig()
        self.hybrid_search = HybridSearchRetriever(db, redis=redis)
        self.reranker = ChunkReranker() if self.config.enable_reranking else None
        self.query_expander = QueryExpander() if self.config.enable_expansion else None

    async def retrieve(
        self,
        user_id: str,
        question: str,
        source_type: str | None = None,
    ) -> str:
        """
        Full advanced retrieval pipeline.

        Args:
            user_id: User whose documents to search.
            question: The interview question to find relevant context for.
            source_type: Optional filter ("resume", "jd", or None for both).

        Returns:
            Formatted context string ready for LLM prompt.
        """
        start = time.monotonic()

        # Step 1: Query Expansion
        queries = [question]
        if self.query_expander and self.config.enable_expansion:
            try:
                queries = await self.query_expander.expand(question)
            except Exception as e:
                log.warning("Query expansion failed", error=str(e))

        # Step 2: Embed original question (for vector search)
        if self.embed_fn is None:
            return "No embedding function configured."

        question_embedding = (await self.embed_fn([question]))[0]

        # Step 3: Hybrid search for each query, then deduplicate
        all_candidates: dict[str, dict] = {}

        # Embed all expanded queries in one batch for efficiency
        if len(queries) > 1:
            all_embeddings = await self.embed_fn(queries)
        else:
            all_embeddings = [question_embedding]

        # Run hybrid search for each query in parallel
        search_tasks = [
            self.hybrid_search.retrieve(
                user_id=user_id,
                question=q,
                question_embedding=emb,
                source_type=source_type,
                top_k=self.config.hybrid_top_k,
                rrf_weight_bm25=self.config.rrf_weight_bm25,
                rrf_weight_vector=self.config.rrf_weight_vector,
            )
            for q, emb in zip(queries, all_embeddings)
        ]
        search_results = await asyncio.gather(*search_tasks)

        # Deduplicate across query expansions, keeping highest RRF score
        for results in search_results:
            for chunk in results:
                chunk_id = chunk["id"]
                existing = all_candidates.get(chunk_id)
                if existing is None or chunk.get("rrf_score", 0) > existing.get("rrf_score", 0):
                    all_candidates[chunk_id] = chunk

        candidates = list(all_candidates.values())

        if not candidates:
            return "No resume context available."

        # Step 4: Cross-Encoder Reranking
        if self.reranker and self.config.enable_reranking and len(candidates) > self.config.final_top_k:
            try:
                candidates = await self.reranker.rerank(
                    question=question,
                    chunks=candidates,
                    top_k=self.config.final_top_k,
                )
            except Exception as e:
                log.warning("Reranking failed, using RRF-ranked results", error=str(e))
                candidates = sorted(
                    candidates,
                    key=lambda x: x.get("rrf_score", 0),
                    reverse=True,
                )[:self.config.final_top_k]
        else:
            # No reranking — take top-k by RRF score
            candidates = sorted(
                candidates,
                key=lambda x: x.get("rrf_score", 0),
                reverse=True,
            )[:self.config.final_top_k]

        # Step 5: Parent Resolution — use parent_text if available
        context_parts = []
        for chunk in candidates:
            # Prefer parent text (full context) over child text
            display_text = chunk.get("parent_text") or chunk["chunk_text"]
            section = chunk.get("section", "general")
            src_type = chunk.get("source_type", "resume")
            section_label = f"[{src_type.upper()} — {section}]"
            context_parts.append(f"{section_label}\n{display_text}")

        elapsed_ms = (time.monotonic() - start) * 1000

        log.info(
            "Advanced retrieval complete",
            queries=len(queries),
            total_candidates=len(all_candidates),
            final_chunks=len(context_parts),
            elapsed_ms=round(elapsed_ms, 1),
        )

        return "\n\n".join(context_parts)
