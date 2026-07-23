import asyncio
from functools import lru_cache

import structlog
from fastembed import TextEmbedding
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.config import get_settings
from app.services.document_parser import DocumentParser, ParsedChunk
from app.services.rag.chunking import ParentChildChunker, ParentChunk
from app.models.document_chunk import DocumentChunk, EMBEDDING_DIM

log = structlog.get_logger()

# Singleton embedding model — loaded once, reused across requests.
# sentence-transformers/all-MiniLM-L6-v2: 384 dims, ~23MB, fast on CPU, great for semantic search.
_embedding_model: TextEmbedding | None = None


def _get_embedding_model() -> TextEmbedding:
    """Lazy-load the fastembed model (singleton)."""
    global _embedding_model
    if _embedding_model is None:
        model_name = get_settings().embedding_model
        supported_models = {m["model"] for m in TextEmbedding.list_supported_models()}
        if model_name not in supported_models:
            log.warning(
                "Configured embedding model not supported by fastembed, falling back to sentence-transformers/all-MiniLM-L6-v2",
                requested_model=model_name,
            )
            model_name = "sentence-transformers/all-MiniLM-L6-v2"
        log.info("Loading fastembed model...", model_name=model_name)
        _embedding_model = TextEmbedding(model_name=model_name)
        log.info("Fastembed model loaded", dimensions=EMBEDDING_DIM)
    return _embedding_model


class RAGService:
    """
    Resume/JD embedding ingestion and retrieval.
    Uses fastembed (all-MiniLM-L6-v2) for free local embeddings
    and pgvector for similarity search.

    Retrieval now delegates to AdvancedRetriever (hybrid search +
    cross-encoder reranking + query expansion) when available.
    """

    def __init__(self, db: AsyncSession, redis=None) -> None:
        self.db = db
        self.redis = redis
        self.parser = DocumentParser()
        self.chunker = ParentChildChunker()
        self.model = _get_embedding_model()

    def _embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts using fastembed (runs locally on CPU)."""
        embeddings = list(self.model.embed(texts))
        return [emb.tolist() for emb in embeddings]

    async def _embed_async(self, texts: list[str]) -> list[list[float]]:
        """Run embedding in a thread pool to avoid blocking the event loop."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._embed, texts)

    async def ingest_resume(
        self,
        user_id: str,
        document_id: str,
        file_bytes: bytes,
        file_type: str,
    ) -> tuple[int, str]:
        """
        Parse resume, embed chunks, store in pgvector.
        Uses parent-child chunking for better retrieval.
        Returns (chunk_count, raw_text).
        """
        raw_text = self.parser.parse_resume(file_bytes, file_type)
        chunks = self.parser.chunk_resume(raw_text)
        count = await self._store_chunks_with_hierarchy(user_id, document_id, chunks)

        # Invalidate BM25 cache for this user
        await self._invalidate_bm25_cache(user_id)

        return count, raw_text

    async def ingest_jd(
        self,
        user_id: str,
        document_id: str,
        jd_text: str,
    ) -> int:
        """Embed JD text, store in pgvector."""
        chunks = self.parser.chunk_jd(jd_text)
        count = await self._store_chunks_with_hierarchy(user_id, document_id, chunks)

        # Invalidate BM25 cache for this user
        await self._invalidate_bm25_cache(user_id)

        return count

    async def _store_chunks_with_hierarchy(
        self,
        user_id: str,
        document_id: str,
        parsed_chunks: list[ParsedChunk],
    ) -> int:
        """
        Store chunks using parent-child hierarchy.
        Creates parent chunks for context and child chunks for embedding.
        """
        if not parsed_chunks:
            return 0

        all_db_chunks: list[DocumentChunk] = []
        child_texts: list[str] = []
        child_chunk_records: list[dict] = []

        for parsed in parsed_chunks:
            # Generate parent-child hierarchy from each parsed chunk
            parents = self.chunker.chunk_document(
                text=parsed.text,
                section=parsed.section,
                source_type=parsed.source_type,
            )

            for parent in parents:
                # Store parent chunk (no embedding — used for context only)
                parent_db = DocumentChunk(
                    id=parent.id,
                    document_id=document_id,
                    user_id=user_id,
                    source_type=parent.source_type,
                    section=parent.section,
                    chunk_text=parent.text,
                    embedding=[0.0] * EMBEDDING_DIM,  # placeholder
                    is_parent=True,
                    parent_id=None,
                    parent_text=None,
                )
                all_db_chunks.append(parent_db)

                # Collect child chunks for batch embedding
                for child in parent.children:
                    child_texts.append(child.text)
                    child_chunk_records.append({
                        "id": child.id,
                        "parent_id": parent.id,
                        "parent_text": parent.text,
                        "document_id": document_id,
                        "user_id": user_id,
                        "source_type": child.source_type,
                        "section": child.section,
                        "chunk_text": child.text,
                    })

        # Batch embed all child chunks
        if child_texts:
            embeddings = await self._embed_async(child_texts)

            for i, record in enumerate(child_chunk_records):
                child_db = DocumentChunk(
                    id=record["id"],
                    document_id=record["document_id"],
                    user_id=record["user_id"],
                    source_type=record["source_type"],
                    section=record["section"],
                    chunk_text=record["chunk_text"],
                    embedding=embeddings[i],
                    is_parent=False,
                    parent_id=record["parent_id"],
                    parent_text=record["parent_text"],
                )
                all_db_chunks.append(child_db)

        self.db.add_all(all_db_chunks)
        await self.db.flush()

        log.info(
            "Chunks stored (parent-child)",
            document_id=document_id,
            total_chunks=len(all_db_chunks),
            parent_chunks=len([c for c in all_db_chunks if c.is_parent]),
            child_chunks=len([c for c in all_db_chunks if not c.is_parent]),
        )
        return len(all_db_chunks)

    async def retrieve(
        self,
        user_id: str,
        question: str,
        source_type: str | None = None,
        top_k: int = 4,
    ) -> str:
        """
        Find most relevant resume/JD chunks for a given question.
        Returns formatted context string for LLM prompt.

        This is the legacy retrieve method kept for backward compatibility.
        The AdvancedRetriever in retriever.py should be used instead
        for the full pipeline.
        """
        question_embedding = (await self._embed_async([question]))[0]

        # Build query with optional source_type filter
        where_clause = "WHERE user_id = :user_id"
        params: dict = {
            "embedding": str(question_embedding),
            "user_id": user_id,
            "top_k": top_k,
        }

        if source_type:
            where_clause += " AND source_type = :source_type"
            params["source_type"] = source_type

        result = await self.db.execute(
            text(f"""
                SELECT chunk_text, section, source_type, parent_text,
                       1 - (embedding <=> CAST(:embedding AS vector)) as similarity
                FROM document_chunks
                {where_clause}
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT :top_k
            """),
            params,
        )

        rows = result.fetchall()
        if not rows:
            return "No resume context available."

        context_parts = []
        for row in rows:
            # Prefer parent text if available (full context)
            display_text = getattr(row, "parent_text", None) or row.chunk_text
            section_label = f"[{row.source_type.upper()} — {row.section}]"
            context_parts.append(f"{section_label}\n{display_text}")

        return "\n\n".join(context_parts)

    async def _invalidate_bm25_cache(self, user_id: str) -> None:
        """Invalidate BM25 cache after chunk ingestion."""
        if self.redis:
            from app.services.rag.hybrid_search import HybridSearchRetriever
            retriever = HybridSearchRetriever(self.db, redis=self.redis)
            await retriever.invalidate_cache(user_id)
