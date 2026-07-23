"""
Unit & Integration Tests for Upgrade Phase E: Context & Memory System.
Tests Semantic Session Memory, Anti-Repetition guidance, Topic Extractor, and Cross-Session Memory.
"""

import pytest
import time
from app.services.memory import (
    MemoryEntry,
    SemanticSessionMemory,
    TopicExtractor,
    CrossSessionMemory,
)


@pytest.mark.asyncio
async def test_semantic_session_memory_add_and_retrieve():
    """Verify storing Q&A entries and retrieving relevant past context based on embedding similarity."""
    memory = SemanticSessionMemory(session_id="test_session_1", redis=None)

    # Add past Q&A entries
    entry1 = MemoryEntry(
        question="Tell me about a project where you scaled a database.",
        answer="I scaled our PostgreSQL cluster at Acme Corp using read replicas.",
        question_type="behavioral",
        timestamp_ms=int(time.time() * 1000) - 10000,
        question_embedding=[1.0, 0.0, 0.0],
        topics_covered=["PostgreSQL", "Scaling"],
        projects_mentioned=["Acme Corp Database Engine"],
        skills_demonstrated=["PostgreSQL"],
    )
    entry2 = MemoryEntry(
        question="How do you handle team conflicts?",
        answer="I schedule 1-on-1 feedback sessions and focus on shared goals.",
        question_type="behavioral",
        timestamp_ms=int(time.time() * 1000) - 5000,
        question_embedding=[0.0, 1.0, 0.0],
        topics_covered=["Leadership"],
        projects_mentioned=[],
        skills_demonstrated=["Communication"],
    )

    await memory.add_entry(entry1)
    await memory.add_entry(entry2)

    # Query with embedding similar to entry1 [1.0, 0.1, 0.0]
    query_emb = [0.99, 0.1, 0.0]
    context_str, metadata = await memory.get_relevant_context(
        current_question="What database performance challenges did you face?",
        current_embedding=query_emb,
    )

    assert "Tell me about a project where you scaled a database." in context_str
    assert metadata["recalled_count"] > 0
    assert "Acme Corp Database Engine" in metadata["projects_avoided"]


@pytest.mark.asyncio
async def test_semantic_session_memory_repetition_warning():
    """Verify explicit anti-repetition guidance is injected when repeat projects or skills exist."""
    memory = SemanticSessionMemory(session_id="test_session_2", redis=None)

    entry = MemoryEntry(
        question="Tell me about your most challenging system design.",
        answer="I built the Payments Gateway Platform using Redis and microservices.",
        question_type="system_design",
        timestamp_ms=int(time.time() * 1000),
        question_embedding=[0.5, 0.5, 0.0],
        topics_covered=["System Design"],
        projects_mentioned=["Payments Gateway Platform"],
        skills_demonstrated=["Redis", "Microservices"],
    )
    await memory.add_entry(entry)

    context_str, metadata = await memory.get_relevant_context(
        current_question="Describe another technical achievement.",
        current_embedding=[0.5, 0.5, 0.0],
    )

    assert "[AVOID REPETITION" in context_str
    assert "Payments Gateway Platform" in context_str
    assert "Redis" in context_str
    assert "Payments Gateway Platform" in metadata["projects_avoided"]


@pytest.mark.asyncio
async def test_topic_extractor_fast_heuristics():
    """Verify TopicExtractor parses project names and skills instantly using local heuristics."""
    extractor = TopicExtractor()

    question = "Tell me about a project you led."
    answer = "I led the development of the Analytics Service using Python and Docker on AWS."

    extracted = await extractor.extract(question, answer, groq_api_key=None)

    assert "Analytics Service" in extracted["projects_mentioned"]
    assert "Python" in extracted["skills_demonstrated"]
    assert "Docker" in extracted["skills_demonstrated"]


@pytest.mark.asyncio
async def test_cross_session_memory_fallback():
    """Verify CrossSessionMemory handles empty or offline database sessions gracefully."""
    class MockResult:
        def scalars(self):
            return self
        def all(self):
            return []

    class MockDB:
        async def execute(self, stmt):
            return MockResult()

    cross_mem = CrossSessionMemory(db=MockDB())
    context = await cross_mem.get_user_performance_context(user_id="user_123")
    assert context == "No previous session history."

    weak_areas = await cross_mem.identify_weak_areas(user_id="user_123")
    assert weak_areas == []
