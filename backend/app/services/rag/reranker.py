"""
Cross-encoder reranking for dramatically improved retrieval precision.

Unlike bi-encoders (which embed query and chunk separately), cross-encoders
read both the question AND each chunk together, producing a much more
accurate relevance score.

Model: cross-encoder/ms-marco-MiniLM-L-6-v2
  - Size: ~90MB
  - Runs on CPU
  - Latency: ~20ms for 8 chunk pairs
  - License: Apache 2.0

Flow:
  1. Hybrid search returns top 8 candidates
  2. Reranker scores each (question, chunk) pair
  3. Return top 4 by reranker score
  4. These 4 chunks go into the LLM prompt
"""

import asyncio

import structlog
from sentence_transformers import CrossEncoder

log = structlog.get_logger()


class ChunkReranker:
    """
    Cross-encoder reranker for retrieved chunks.
    Uses a singleton model instance to avoid repeated loading.
    """

    _model: CrossEncoder | None = None
    _model_lock = asyncio.Lock()

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name

    async def _get_model(self) -> CrossEncoder:
        """Lazy-load the cross-encoder model (thread-safe singleton)."""
        async with self._class_lock():
            if ChunkReranker._model is None:
                log.info("Loading reranker model", model=self.model_name)
                ChunkReranker._model = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: CrossEncoder(
                        self.model_name,
                        max_length=512,
                    ),
                )
                log.info("Reranker model loaded", model=self.model_name)
        return ChunkReranker._model

    @classmethod
    def _class_lock(cls):
        """Return the class-level asyncio lock."""
        return cls._model_lock

    async def rerank(
        self,
        question: str,
        chunks: list[dict],
        top_k: int = 4,
    ) -> list[dict]:
        """
        Rerank chunks by relevance to the question using cross-encoder.

        Args:
            question: The interview question.
            chunks: List of chunk dicts (must have "chunk_text" key).
            top_k: Number of most relevant chunks to return.

        Returns:
            Top-k chunks sorted by cross-encoder relevance score,
            each annotated with "reranker_score".
        """
        if not chunks:
            return []

        model = await self._get_model()

        # Create (question, chunk) pairs for the cross-encoder
        pairs = [(question, chunk["chunk_text"]) for chunk in chunks]

        # Score all pairs in executor to avoid blocking event loop
        scores = await asyncio.get_event_loop().run_in_executor(
            None,
            model.predict,
            pairs,
        )

        # Sort by reranker score descending
        scored_chunks = sorted(
            zip(chunks, scores),
            key=lambda x: float(x[1]),
            reverse=True,
        )

        top_chunks = [
            {**chunk, "reranker_score": float(score)}
            for chunk, score in scored_chunks[:top_k]
        ]

        log.debug(
            "Reranking complete",
            input_chunks=len(chunks),
            output_chunks=len(top_chunks),
            top_score=float(scored_chunks[0][1]) if scored_chunks else 0,
            bottom_score=float(scored_chunks[-1][1]) if scored_chunks else 0,
        )

        return top_chunks
