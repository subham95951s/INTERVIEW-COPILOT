"""
Hybrid retrieval: BM25 (lexical) + pgvector (semantic).
Combined with Reciprocal Rank Fusion (RRF).

Why hybrid:
  BM25 finds exact keyword matches: "React", "AWS", "2019"
  Vector finds semantic matches: "frontend development" ≈ "React developer"
  RRF combines both rankings for best of both worlds.

BM25 corpus is cached in Redis per-user with a 10-minute TTL to avoid
repeated database loads during a session.
"""

import asyncio
import json
from collections import defaultdict

import numpy as np
import structlog
from rank_bm25 import BM25Okapi
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

log = structlog.get_logger()

# Redis key prefix and TTL for BM25 corpus caching
_BM25_CACHE_PREFIX = "bm25_corpus:"
_BM25_CACHE_TTL = 600  # 10 minutes


class HybridSearchRetriever:
    """
    Combines BM25 lexical search with pgvector semantic search.
    Uses Reciprocal Rank Fusion (RRF) to merge results.

    BM25 corpus for each user is cached in Redis to avoid
    loading all chunks on every retrieval call.
    """

    RRF_K = 60  # Standard RRF constant

    def __init__(self, db: AsyncSession, redis=None) -> None:
        self.db = db
        self.redis = redis

    async def retrieve(
        self,
        user_id: str,
        question: str,
        question_embedding: list[float],
        source_type: str | None = None,
        top_k: int = 8,
        rrf_weight_bm25: float = 0.4,
        rrf_weight_vector: float = 0.6,
    ) -> list[dict]:
        """
        Retrieve chunks using hybrid BM25 + vector search.
        Returns top_k chunks sorted by RRF score.
        """
        # Run both searches in parallel
        bm25_results, vector_results = await asyncio.gather(
            self._bm25_search(user_id, question, source_type, top_k * 2),
            self._vector_search(user_id, question_embedding, source_type, top_k * 2),
        )

        # Reciprocal Rank Fusion
        rrf_scores: dict[str, float] = defaultdict(float)
        chunk_data: dict[str, dict] = {}

        for rank, chunk in enumerate(bm25_results):
            chunk_id = chunk["id"]
            rrf_scores[chunk_id] += rrf_weight_bm25 / (self.RRF_K + rank + 1)
            chunk_data[chunk_id] = chunk

        for rank, chunk in enumerate(vector_results):
            chunk_id = chunk["id"]
            rrf_scores[chunk_id] += rrf_weight_vector / (self.RRF_K + rank + 1)
            chunk_data[chunk_id] = chunk

        # Sort by RRF score and return top_k
        sorted_ids = sorted(
            rrf_scores.keys(),
            key=lambda x: rrf_scores[x],
            reverse=True,
        )

        results = [
            {**chunk_data[chunk_id], "rrf_score": rrf_scores[chunk_id]}
            for chunk_id in sorted_ids[:top_k]
        ]

        log.debug(
            "Hybrid search complete",
            bm25_hits=len(bm25_results),
            vector_hits=len(vector_results),
            fused_results=len(results),
        )

        return results

    async def _bm25_search(
        self,
        user_id: str,
        query: str,
        source_type: str | None,
        top_k: int,
    ) -> list[dict]:
        """BM25 lexical search against stored chunks, with Redis caching."""
        corpus_rows = await self._load_corpus(user_id, source_type)

        if not corpus_rows:
            return []

        # Tokenize corpus and query
        corpus_texts = [row["chunk_text"].lower().split() for row in corpus_rows]
        bm25 = BM25Okapi(corpus_texts)
        query_tokens = query.lower().split()
        scores = bm25.get_scores(query_tokens)

        # Return top_k by BM25 score (only positive scores)
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [
            {
                "id": corpus_rows[i]["id"],
                "chunk_text": corpus_rows[i]["chunk_text"],
                "section": corpus_rows[i]["section"],
                "source_type": corpus_rows[i]["source_type"],
                "parent_id": corpus_rows[i].get("parent_id"),
                "parent_text": corpus_rows[i].get("parent_text"),
                "bm25_score": float(scores[i]),
            }
            for i in top_indices if scores[i] > 0
        ]

    async def _load_corpus(
        self,
        user_id: str,
        source_type: str | None,
    ) -> list[dict]:
        """
        Load all chunks for a user, with Redis caching.
        Cache key includes source_type filter.
        """
        cache_key = f"{_BM25_CACHE_PREFIX}{user_id}:{source_type or 'all'}"

        # Try Redis cache first
        if self.redis:
            try:
                cached = await self.redis.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception:
                pass  # Fall through to DB

        # Load from database
        where_clause = "WHERE user_id = :user_id"
        params: dict = {"user_id": user_id}

        if source_type:
            where_clause += " AND source_type = :source_type"
            params["source_type"] = source_type

        result = await self.db.execute(
            text(f"""
                SELECT id, chunk_text, section, source_type, parent_id, parent_text
                FROM document_chunks
                {where_clause}
            """),
            params,
        )
        rows = result.fetchall()

        corpus = [
            {
                "id": row.id,
                "chunk_text": row.chunk_text,
                "section": row.section,
                "source_type": row.source_type,
                "parent_id": getattr(row, "parent_id", None),
                "parent_text": getattr(row, "parent_text", None),
            }
            for row in rows
        ]

        # Cache in Redis with TTL
        if self.redis and corpus:
            try:
                await self.redis.set(
                    cache_key,
                    json.dumps(corpus),
                    ex=_BM25_CACHE_TTL,
                )
            except Exception:
                pass  # Non-critical

        return corpus

    async def _vector_search(
        self,
        user_id: str,
        embedding: list[float],
        source_type: str | None,
        top_k: int,
    ) -> list[dict]:
        """pgvector cosine similarity search."""
        where_clause = "WHERE user_id = :user_id AND is_parent = false"
        params: dict = {
            "emb": str(embedding),
            "user_id": user_id,
            "k": top_k,
        }

        if source_type:
            where_clause += " AND source_type = :source_type"
            params["source_type"] = source_type

        result = await self.db.execute(
            text(f"""
                SELECT id, chunk_text, section, source_type,
                       parent_id, parent_text,
                       1 - (embedding <=> CAST(:emb AS vector)) as similarity
                FROM document_chunks
                {where_clause}
                ORDER BY embedding <=> CAST(:emb AS vector)
                LIMIT :k
            """),
            params,
        )
        return [
            {
                "id": row.id,
                "chunk_text": row.chunk_text,
                "section": row.section,
                "source_type": row.source_type,
                "parent_id": getattr(row, "parent_id", None),
                "parent_text": getattr(row, "parent_text", None),
                "vector_score": float(row.similarity),
            }
            for row in result.fetchall()
        ]

    async def invalidate_cache(self, user_id: str) -> None:
        """Invalidate BM25 cache when chunks are added/removed for a user."""
        if self.redis:
            try:
                # Delete all cached corpus keys for this user
                async for key in self.redis.scan_iter(
                    match=f"{_BM25_CACHE_PREFIX}{user_id}:*"
                ):
                    await self.redis.delete(key)
            except Exception:
                pass
