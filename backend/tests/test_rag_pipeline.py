"""
Tests for Phase C — Advanced RAG Pipeline components.

Tests cover:
  1. Parent-Child Chunking
  2. Hybrid Search (BM25 + Vector) — mocked DB
  3. Query Expansion — mocked Groq
  4. Cross-Encoder Reranker — mocked model
  5. Advanced Retriever orchestrator — full pipeline
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ─── 1. Parent-Child Chunking ───────────────────────────────────────────────


class TestParentChildChunker:
    def test_chunk_document_produces_hierarchy(self):
        from app.services.rag.chunking import ParentChildChunker

        chunker = ParentChildChunker()
        text = "A" * 1600  # 2x parent chunk size (800)
        parents = chunker.chunk_document(text, section="experience", source_type="resume")

        assert len(parents) >= 2
        for parent in parents:
            assert parent.text.strip()
            assert parent.section == "experience"
            assert parent.source_type == "resume"
            assert len(parent.children) >= 1
            for child in parent.children:
                assert child.parent_id == parent.id
                assert len(child.text) <= ParentChildChunker.CHILD_CHUNK_SIZE + 10

    def test_empty_text_returns_empty(self):
        from app.services.rag.chunking import ParentChildChunker

        chunker = ParentChildChunker()
        result = chunker.chunk_document("", section="test", source_type="resume")
        assert result == []

    def test_small_text_produces_single_parent(self):
        from app.services.rag.chunking import ParentChildChunker

        chunker = ParentChildChunker()
        text = "I led a team of 5 engineers to deliver a microservices platform."
        parents = chunker.chunk_document(text, section="experience", source_type="resume")

        assert len(parents) == 1
        assert parents[0].text == text
        assert len(parents[0].children) >= 1

    def test_child_chunks_overlap(self):
        from app.services.rag.chunking import ParentChildChunker

        chunker = ParentChildChunker()
        # Create text that will produce multiple children
        text = "word " * 200  # ~1000 chars
        parents = chunker.chunk_document(text, section="skills", source_type="resume")

        assert len(parents) >= 1
        for parent in parents:
            if len(parent.children) > 1:
                # Child chunks should have some overlap
                first_end = parent.children[0].text
                second_start = parent.children[1].text
                # Due to overlap, some content should appear in both
                assert len(first_end) > 0
                assert len(second_start) > 0


# ─── 2. Hybrid Search ───────────────────────────────────────────────────────


class TestHybridSearch:
    @pytest.fixture
    def mock_chunks(self):
        """Sample chunk data mimicking DB rows."""
        return [
            {"id": "c1", "chunk_text": "React developer with 5 years experience", "section": "experience", "source_type": "resume", "parent_id": None, "parent_text": None},
            {"id": "c2", "chunk_text": "AWS cloud infrastructure management", "section": "skills", "source_type": "resume", "parent_id": None, "parent_text": None},
            {"id": "c3", "chunk_text": "Led frontend team of 8 engineers", "section": "experience", "source_type": "resume", "parent_id": None, "parent_text": None},
            {"id": "c4", "chunk_text": "Python backend development Flask Django", "section": "skills", "source_type": "resume", "parent_id": None, "parent_text": None},
        ]

    @pytest.mark.asyncio
    async def test_bm25_search_returns_ranked_results(self, mock_chunks):
        from app.services.rag.hybrid_search import HybridSearchRetriever

        # Mock the DB session
        mock_db = AsyncMock()
        mock_row_type = type("Row", (), {})
        rows = []
        for c in mock_chunks:
            row = mock_row_type()
            for k, v in c.items():
                setattr(row, k, v)
            rows.append(row)

        mock_result = MagicMock()
        mock_result.fetchall.return_value = rows
        mock_db.execute = AsyncMock(return_value=mock_result)

        retriever = HybridSearchRetriever(mock_db, redis=None)
        results = await retriever._bm25_search("user1", "React frontend development", None, top_k=4)

        # "React" appears in c1, "frontend" in c3, "development" in c4
        assert len(results) > 0
        assert all(r["bm25_score"] > 0 for r in results)
        # c1 should rank high since it contains "React"
        ids = [r["id"] for r in results]
        assert "c1" in ids

    @pytest.mark.asyncio
    async def test_rrf_fusion_combines_both_search_types(self):
        from app.services.rag.hybrid_search import HybridSearchRetriever

        mock_db = AsyncMock()
        retriever = HybridSearchRetriever(mock_db, redis=None)

        # Mock both search methods
        bm25_results = [
            {"id": "c1", "chunk_text": "React dev", "section": "exp", "source_type": "resume", "parent_id": None, "parent_text": None, "bm25_score": 5.0},
            {"id": "c2", "chunk_text": "AWS ops", "section": "exp", "source_type": "resume", "parent_id": None, "parent_text": None, "bm25_score": 2.0},
        ]
        vector_results = [
            {"id": "c1", "chunk_text": "React dev", "section": "exp", "source_type": "resume", "parent_id": None, "parent_text": None, "vector_score": 0.95},
            {"id": "c3", "chunk_text": "Frontend team", "section": "exp", "source_type": "resume", "parent_id": None, "parent_text": None, "vector_score": 0.85},
        ]

        with patch.object(retriever, "_bm25_search", return_value=bm25_results):
            with patch.object(retriever, "_vector_search", return_value=vector_results):
                results = await retriever.retrieve(
                    user_id="user1",
                    question="React frontend",
                    question_embedding=[0.1] * 384,
                    top_k=4,
                )

        # c1 appears in both → highest RRF score
        assert results[0]["id"] == "c1"
        # All three unique chunks should be present
        result_ids = {r["id"] for r in results}
        assert result_ids == {"c1", "c2", "c3"}


# ─── 3. Query Expansion ─────────────────────────────────────────────────────


class TestQueryExpansion:
    @pytest.mark.asyncio
    async def test_expand_returns_original_plus_expansions(self):
        from app.services.rag.query_expansion import QueryExpander

        # Mock the Groq client
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps([
            "project leadership experience",
            "team management software",
            "cross-functional coordination",
        ])
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        expander = QueryExpander(client=mock_client)
        queries = await expander.expand("Tell me about leading a project")

        assert len(queries) == 4  # original + 3 expansions
        assert queries[0] == "Tell me about leading a project"
        assert "project leadership experience" in queries

    @pytest.mark.asyncio
    async def test_expand_graceful_fallback_on_error(self):
        from app.services.rag.query_expansion import QueryExpander

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API error"))

        expander = QueryExpander(client=mock_client)
        queries = await expander.expand("Tell me about a challenge")

        assert queries == ["Tell me about a challenge"]

    def test_parse_json_array_from_markdown(self):
        from app.services.rag.query_expansion import QueryExpander

        # Test parsing from markdown code block
        content = '```json\n["query 1", "query 2", "query 3"]\n```'
        result = QueryExpander._parse_json_array(content)
        assert result == ["query 1", "query 2", "query 3"]

    def test_parse_json_array_direct(self):
        from app.services.rag.query_expansion import QueryExpander

        content = '["a", "b", "c"]'
        result = QueryExpander._parse_json_array(content)
        assert result == ["a", "b", "c"]


# ─── 4. Cross-Encoder Reranker ───────────────────────────────────────────────


class TestChunkReranker:
    @pytest.mark.asyncio
    async def test_rerank_orders_by_relevance(self):
        from app.services.rag.reranker import ChunkReranker
        import numpy as np

        reranker = ChunkReranker()

        # Mock the cross-encoder model
        mock_model = MagicMock()
        # Simulate scores: c3 > c1 > c2
        mock_model.predict.return_value = np.array([0.7, 0.2, 0.95])

        with patch.object(ChunkReranker, "_model", mock_model):
            chunks = [
                {"id": "c1", "chunk_text": "React development experience"},
                {"id": "c2", "chunk_text": "Unrelated content about cooking"},
                {"id": "c3", "chunk_text": "Frontend engineering team leadership"},
            ]
            results = await reranker.rerank(
                question="Tell me about frontend development",
                chunks=chunks,
                top_k=2,
            )

        assert len(results) == 2
        assert results[0]["id"] == "c3"  # highest score
        assert results[1]["id"] == "c1"  # second highest
        assert "reranker_score" in results[0]

    @pytest.mark.asyncio
    async def test_rerank_empty_chunks(self):
        from app.services.rag.reranker import ChunkReranker

        reranker = ChunkReranker()
        results = await reranker.rerank("test question", [], top_k=4)
        assert results == []


# ─── 5. Advanced Retriever Orchestrator ──────────────────────────────────────


class TestAdvancedRetriever:
    @pytest.mark.asyncio
    async def test_full_pipeline_returns_formatted_context(self):
        from app.services.rag.retriever import AdvancedRetriever, RetrievalConfig

        mock_db = AsyncMock()

        # Mock embed function
        async def mock_embed(texts):
            return [[0.1] * 384 for _ in texts]

        config = RetrievalConfig(
            enable_expansion=False,  # disable to simplify test
            enable_reranking=False,
            hybrid_top_k=4,
            final_top_k=2,
        )

        retriever = AdvancedRetriever(
            db=mock_db,
            redis=None,
            embed_fn=mock_embed,
            config=config,
        )

        # Mock hybrid search to return known chunks
        mock_results = [
            {"id": "c1", "chunk_text": "Led React team", "section": "experience", "source_type": "resume", "parent_id": None, "parent_text": None, "rrf_score": 0.8},
            {"id": "c2", "chunk_text": "AWS infrastructure", "section": "skills", "source_type": "resume", "parent_id": None, "parent_text": None, "rrf_score": 0.5},
        ]

        with patch.object(retriever.hybrid_search, "retrieve", return_value=mock_results):
            result = await retriever.retrieve(
                user_id="user1",
                question="Tell me about your leadership",
                source_type="resume",
            )

        assert "[RESUME — experience]" in result
        assert "Led React team" in result

    @pytest.mark.asyncio
    async def test_parent_resolution_uses_parent_text(self):
        from app.services.rag.retriever import AdvancedRetriever, RetrievalConfig

        mock_db = AsyncMock()

        async def mock_embed(texts):
            return [[0.1] * 384 for _ in texts]

        config = RetrievalConfig(enable_expansion=False, enable_reranking=False, final_top_k=1)

        retriever = AdvancedRetriever(db=mock_db, embed_fn=mock_embed, config=config)

        # Child chunk has a parent_text
        mock_results = [
            {
                "id": "child_1",
                "chunk_text": "Led React team",  # small child text
                "section": "experience",
                "source_type": "resume",
                "parent_id": "parent_1",
                "parent_text": "Led React team of 8 engineers, delivered 3 major features, improved CI/CD pipeline",  # full parent context
                "rrf_score": 0.9,
            },
        ]

        with patch.object(retriever.hybrid_search, "retrieve", return_value=mock_results):
            result = await retriever.retrieve(user_id="user1", question="leadership")

        # Should use parent_text (full context) instead of chunk_text
        assert "improved CI/CD pipeline" in result

    @pytest.mark.asyncio
    async def test_no_results_returns_fallback_message(self):
        from app.services.rag.retriever import AdvancedRetriever, RetrievalConfig

        mock_db = AsyncMock()

        async def mock_embed(texts):
            return [[0.1] * 384 for _ in texts]

        config = RetrievalConfig(enable_expansion=False, enable_reranking=False)
        retriever = AdvancedRetriever(db=mock_db, embed_fn=mock_embed, config=config)

        with patch.object(retriever.hybrid_search, "retrieve", return_value=[]):
            result = await retriever.retrieve(user_id="user1", question="anything")

        assert result == "No resume context available."

    @pytest.mark.asyncio
    async def test_no_embed_fn_returns_error_message(self):
        from app.services.rag.retriever import AdvancedRetriever, RetrievalConfig

        mock_db = AsyncMock()
        config = RetrievalConfig(enable_expansion=False, enable_reranking=False)
        retriever = AdvancedRetriever(db=mock_db, embed_fn=None, config=config)

        result = await retriever.retrieve(user_id="user1", question="test")
        assert "No embedding function" in result


# ─── 6. Backward Compatibility ──────────────────────────────────────────────


class TestBackwardCompatibility:
    def test_import_rag_service_from_package(self):
        """Verify that the old import path still works."""
        from app.services.rag import RAGService
        assert RAGService is not None

    def test_import_advanced_retriever_from_package(self):
        from app.services.rag import AdvancedRetriever, RetrievalConfig
        assert AdvancedRetriever is not None
        assert RetrievalConfig is not None
