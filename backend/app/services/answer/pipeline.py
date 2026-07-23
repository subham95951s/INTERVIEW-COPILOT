"""Multi-Step Answer Generation Pipeline with Grounding & Self-Evaluation."""

import asyncio
from dataclasses import dataclass
import structlog

from app.services.answer.prompt_templates import (
    QuestionType,
    classify_question_type,
    get_type_specific_prompt,
)
from app.services.answer.cache import AnswerCache
from app.services.answer.hallucination_guard import HallucinationGuard

log = structlog.get_logger()


@dataclass
class AnswerPipelineResult:
    draft: str
    final_answer: str
    question_type: str
    confidence_score: float
    star_completeness: dict[str, int]
    hallucination_risk: str
    is_cached: bool = False
    revised: bool = False
    memory_context: dict | None = None


class AnswerGenerationPipeline:
    """Orchestrates multi-step answer generation, semantic caching, and hallucination verification."""

    def __init__(
        self,
        llm_provider,
        redis=None,
        embed_fn=None,
        groq_api_key: str | None = None,
    ) -> None:
        self.llm_provider = llm_provider
        self.cache = AnswerCache(redis) if redis else None
        self.embed_fn = embed_fn
        self.guard = HallucinationGuard(api_key=groq_api_key)

    async def run(
        self,
        session_id: str,
        question: str,
        llm_context,
        stream_callback,
        memory_context: dict | None = None,
    ) -> AnswerPipelineResult:
        """Execute the multi-step answer pipeline.

        stream_callback is an async function taking a dict message payload.
        """
        # 1. Classify question type (<0.1ms regex)
        question_type = classify_question_type(question)

        # 2. Check semantic cache
        question_embedding = None
        if self.cache and self.embed_fn:
            try:
                question_embedding = await self.embed_fn(question)
                cached = await self.cache.get_cached_answer(
                    session_id=session_id,
                    question=question,
                    question_embedding=question_embedding,
                )
                if cached:
                    cached_answer = cached["answer"]
                    meta = cached.get("metadata", {})
                    # Stream cached answer tokens quickly
                    await stream_callback({"type": "answer_token", "token": cached_answer})
                    meta_payload = {
                        "type": "answer_metadata",
                        "question_type": question_type.value,
                        "confidence": meta.get("confidence", 0.98),
                        "star_scores": meta.get(
                            "star_scores", {"situation": 3, "task": 3, "action": 3, "result": 3}
                        ),
                        "hallucination_risk": "low",
                        "is_cached": True,
                        "memory_context": memory_context,
                    }
                    await stream_callback(meta_payload)
                    return AnswerPipelineResult(
                        draft=cached_answer,
                        final_answer=cached_answer,
                        question_type=question_type.value,
                        confidence_score=meta_payload["confidence"],
                        star_completeness=meta_payload["star_scores"],
                        hallucination_risk="low",
                        is_cached=True,
                        revised=False,
                        memory_context=memory_context,
                    )
            except Exception as exc:
                log.warning("Cache retrieval skipped", error=str(exc))

        # 3. Format type-specific prompt
        original_question = llm_context.question
        llm_context.question = get_type_specific_prompt(
            base_prompt="Answer the following interview question accurately based on the candidate context.",
            question_type=question_type,
            question=original_question,
        )

        # 4. Stream draft answer immediately
        draft_tokens: list[str] = []
        async for token in self.llm_provider.generate_stream(llm_context):
            draft_tokens.append(token)
            await stream_callback({"type": "answer_token", "token": token})

        draft_answer = "".join(draft_tokens)

        # Calculate base STAR completeness scores based on structure & length
        star_scores = self._estimate_star_scores(question_type, draft_answer)

        # 5. Run asynchronous Hallucination verification against resume context
        guard_res = await self.guard.check_answer(
            answer=draft_answer,
            resume_context=llm_context.rag_chunks,
        )

        confidence = guard_res["confidence"]
        hallucinated_claims = guard_res["hallucinated_claims"]
        hallucination_risk = "high" if not guard_res["safe"] else "low"

        meta_payload = {
            "type": "answer_metadata",
            "question_type": question_type.value,
            "confidence": confidence,
            "star_scores": star_scores,
            "hallucination_risk": hallucination_risk,
            "is_cached": False,
            "memory_context": memory_context,
        }
        await stream_callback(meta_payload)

        # 6. If hallucinated claims detected, generate revised grounded answer
        final_answer = draft_answer
        revised = False

        if hallucinated_claims:
            log.info("Generating grounded revision", hallucinated_count=len(hallucinated_claims))
            revised = True
            revision_prompt = f"""Revise this interview answer to ensure 100% strict grounding in the candidate's actual background context.
Remove or correct these unverified claims: {', '.join(hallucinated_claims)}.

Original Draft Answer:
{draft_answer}

Candidate Actual Background Context:
{llm_context.rag_chunks}

Revised Grounded Answer:"""

            llm_context.question = revision_prompt
            revised_tokens: list[str] = []
            async for token in self.llm_provider.generate_stream(llm_context):
                revised_tokens.append(token)
                await stream_callback({"type": "revision_token", "token": token})

            final_answer = "".join(revised_tokens)
            await stream_callback({"type": "revision_complete"})

        # 7. Store in semantic cache
        if self.cache and question_embedding:
            try:
                await self.cache.cache_answer(
                    session_id=session_id,
                    question=original_question,
                    answer=final_answer,
                    embedding=question_embedding,
                    metadata={
                        "confidence": confidence,
                        "star_scores": star_scores,
                        "question_type": question_type.value,
                    },
                )
            except Exception as exc:
                log.warning("Cache write skipped", error=str(exc))

        return AnswerPipelineResult(
            draft=draft_answer,
            final_answer=final_answer,
            question_type=question_type.value,
            confidence_score=confidence,
            star_completeness=star_scores,
            hallucination_risk=hallucination_risk,
            is_cached=False,
            revised=revised,
            memory_context=memory_context,
        )

    def _estimate_star_scores(self, question_type: QuestionType, answer: str) -> dict[str, int]:
        """Estimate STAR completeness score based on structure and presence of concrete details."""
        words = answer.split()
        length = len(words)

        scores = {"situation": 2, "task": 2, "action": 2, "result": 2}
        if length >= 50:
            scores["situation"] = 3
            scores["task"] = 3
        if length >= 90:
            scores["action"] = 3
        # Check for numeric metrics / % / $ in result
        if any(c.isdigit() or c in "%$" for c in answer):
            scores["result"] = 3

        return scores
