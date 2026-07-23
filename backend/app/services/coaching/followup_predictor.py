"""
Follow-Up Question Predictor — Predicts likely follow-up questions and primes AnswerCache.

Runs asynchronously after answer generation completes so zero latency overhead
is added to the live streaming answer.
"""

import asyncio
import json
import structlog
from groq import AsyncGroq

log = structlog.get_logger()

PREDICT_PROMPT = """Given this interview question and the candidate's answer, predict the top 2 follow-up questions the interviewer is most likely to ask next to probe deeper into technical depth or edge cases.

Question: {question}
Answer: {answer}

Return ONLY a valid JSON array of 2 string questions:
["Follow-up question 1?", "Follow-up question 2?"]"""


class FollowUpPredictor:
    """Predicts next likely interview questions and pre-caches draft answers."""

    def __init__(self, api_key: str | None = None, cache=None) -> None:
        self.api_key = api_key
        self.cache = cache
        self._client: AsyncGroq | None = None
        if api_key:
            self._client = AsyncGroq(api_key=api_key)

    async def predict_followups(
        self,
        question: str,
        answer: str,
    ) -> list[str]:
        """Predict the top 2 likely follow-up questions."""
        if not self._client or not answer.strip():
            return []

        try:
            response = await self._client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {
                        "role": "user",
                        "content": PREDICT_PROMPT.format(
                            question=question[:200],
                            answer=answer[:800],
                        ),
                    }
                ],
                temperature=0.3,
                max_tokens=100,
            )
            content = response.choices[0].message.content or "[]"
            start_idx = content.find("[")
            end_idx = content.rfind("]")
            if start_idx != -1 and end_idx != -1:
                parsed = json.loads(content[start_idx : end_idx + 1])
                if isinstance(parsed, list):
                    return [str(q).strip() for q in parsed[:2] if str(q).strip()]
            return []
        except Exception as exc:
            log.debug("Follow-up prediction error", error=str(exc))
            return []
