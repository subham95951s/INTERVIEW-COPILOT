"""Unit and integration tests for Upgrade Phase D: Answer Quality & Intelligence Pipeline."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from app.services.answer.prompt_templates import (
    QuestionType,
    classify_question_type,
    get_type_specific_prompt,
)
from app.services.answer.cache import AnswerCache
from app.services.answer.hallucination_guard import HallucinationGuard
from app.services.answer.pipeline import AnswerGenerationPipeline
from app.services.llm_router import LLMContext


def test_classify_question_type_regex():
    """Verify ultra-fast regex classifier correctly identifies question types."""
    assert classify_question_type("Design a distributed rate limiter for high throughput") == QuestionType.SYSTEM_DESIGN
    assert classify_question_type("Tell me about a time you resolved a team conflict") == QuestionType.BEHAVIORAL
    assert classify_question_type("Write a function to find the time complexity of binary tree search") == QuestionType.CODING
    assert classify_question_type("Explain the difference between async and thread concurrency") == QuestionType.TECHNICAL
    assert classify_question_type("Why do you want to work at our company?") == QuestionType.MOTIVATION


def test_get_type_specific_prompt():
    """Verify prompt formatting injects required structure rules."""
    prompt = get_type_specific_prompt(
        base_prompt="Answer the question accurately.",
        question_type=QuestionType.BEHAVIORAL,
        question="Tell me about a time you fixed a production outage.",
    )
    assert "STAR (Situation -> Task -> Action -> Result)" in prompt
    assert "Tell me about a time you fixed a production outage." in prompt


@pytest.mark.asyncio
async def test_answer_cache_semantic_hit():
    """Verify cosine similarity >= 0.92 returns instant cache hit."""
    mock_redis = MagicMock()
    # Mock scan_iter returning one key
    async def mock_scan_iter(match=None):
        yield "answer_cache:test_session:123"

    mock_redis.scan_iter = mock_scan_iter
    stored_data = {
        "question": "Can you tell me about a time you led a project?",
        "answer": "I led the migration of our core payment database...",
        "embedding": [1.0, 0.0, 0.0],
        "metadata": {"confidence": 0.96},
    }
    mock_redis.get = AsyncMock(return_value=import_json_dumps(stored_data))

    cache = AnswerCache(mock_redis)

    # 1. Very similar embedding -> hit
    res_hit = await cache.get_cached_answer(
        session_id="test_session",
        question="Tell me about a time you led a major project?",
        question_embedding=[0.99, 0.1, 0.0],
    )
    assert res_hit is not None
    assert res_hit["answer"] == stored_data["answer"]
    assert res_hit["similarity"] >= 0.92

    # 2. Dissimilar embedding -> miss
    res_miss = await cache.get_cached_answer(
        session_id="test_session",
        question="Explain Kubernetes pods",
        question_embedding=[0.0, 1.0, 0.0],
    )
    assert res_miss is None


def import_json_dumps(obj):
    import json
    return json.dumps(obj)


@pytest.mark.asyncio
async def test_hallucination_guard_offline_baseline():
    """Verify HallucinationGuard returns safe baseline when API key not configured."""
    guard = HallucinationGuard(api_key=None)
    res = await guard.check_answer(
        answer="I led a team of 5 engineers.",
        resume_context="Senior Engineer with 6 years experience.",
    )
    assert res["safe"] is True
    assert res["confidence"] >= 0.90


@pytest.mark.asyncio
async def test_answer_pipeline_stream_and_metadata():
    """Verify pipeline streams draft tokens and emits metadata accurately."""
    mock_provider = MagicMock()

    async def mock_gen_stream(context):
        for token in ["I ", "built ", "the ", "API."]:
            yield token

    mock_provider.generate_stream = mock_gen_stream

    pipeline = AnswerGenerationPipeline(
        llm_provider=mock_provider,
        redis=None,
        embed_fn=None,
        groq_api_key=None,
    )

    context = LLMContext(
        candidate_name="Alex",
        rag_chunks="Experienced Python backend developer.",
        jd_summary="Senior Backend Engineer",
        conversation_history=[],
        question="Tell me about a time you designed an API.",
    )

    emitted_messages = []

    async def stream_callback(payload):
        emitted_messages.append(payload)

    result = await pipeline.run(
        session_id="test_sess",
        question=context.question,
        llm_context=context,
        stream_callback=stream_callback,
    )

    assert result.draft == "I built the API."
    assert result.final_answer == "I built the API."
    assert result.question_type == "behavioral"
    assert any(m["type"] == "answer_metadata" for m in emitted_messages)
    token_msgs = [m["token"] for m in emitted_messages if m["type"] == "answer_token"]
    assert "".join(token_msgs) == "I built the API."


def test_user_reported_question_classifications():
    """Verify that conversational, design, and technical questions do not fall back to behavioral STAR format."""
    assert classify_question_type("Who is Sachin Tendulkar?") == QuestionType.CONVERSATIONAL
    assert classify_question_type("Do you have any questions for me about the team or the role?") == QuestionType.CONVERSATIONAL
    assert classify_question_type("How would you design the model synchronization and caching strategy?") == QuestionType.SYSTEM_DESIGN
    assert classify_question_type("How would you evaluate and choose between using a massive state of the art proprietary ML pipeline API versus fine tuning a smaller open source model?") in (QuestionType.SITUATIONAL, QuestionType.TECHNICAL)

