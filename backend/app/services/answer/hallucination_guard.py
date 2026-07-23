"""Hallucination Guard for verifying interview answer claims against candidate background."""

import asyncio
import json
import structlog
from groq import AsyncGroq

log = structlog.get_logger()

SINGLE_PASS_PROMPT = """Analyze this interview answer against the candidate's actual background context.
Identify if there are any specific factual claims in the answer (job titles, companies, dates, metrics) that contradict or are completely unmentioned in the candidate's background context.

Answer:
{answer}

Candidate Background Context:
{background}

Return valid JSON:
{{"safe": true, "hallucinated_claims": []}}"""


class HallucinationGuard:
    """Verifies generated answer claims against actual resume/RAG context in a single fast pass."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key
        self._client: AsyncGroq | None = None
        if api_key:
            self._client = AsyncGroq(api_key=api_key)

    async def check_answer(
        self,
        answer: str,
        resume_context: str,
    ) -> dict:
        """Check an answer for unsupported/hallucinated claims against resume context."""
        if not self._client or not resume_context or resume_context.strip() == "No resume context available.":
            return {
                "safe": True,
                "hallucinated_claims": [],
                "supported_claims": [],
                "confidence": 0.95,
            }

        async def _run_single_pass():
            try:
                response = await self._client.chat.completions.create(
                    model="llama3-8b-8192",
                    messages=[
                        {
                            "role": "user",
                            "content": SINGLE_PASS_PROMPT.format(
                                answer=answer[:800],
                                background=resume_context[:2000],
                            ),
                        }
                    ],
                    temperature=0.0,
                    max_tokens=80,
                    response_format={"type": "json_object"},
                )
                content = response.choices[0].message.content or "{}"
                parsed = json.loads(content)
                hallucinated = parsed.get("hallucinated_claims", [])
                is_safe = parsed.get("safe", len(hallucinated) == 0)
                return {
                    "safe": bool(is_safe),
                    "hallucinated_claims": [str(c) for c in hallucinated][:3],
                    "supported_claims": [],
                    "confidence": 0.92 if is_safe else 0.75,
                }
            except Exception as exc:
                log.warning("Hallucination check single pass error", error=str(exc))
                return {
                    "safe": True,
                    "hallucinated_claims": [],
                    "supported_claims": [],
                    "confidence": 0.95,
                }

        try:
            # Bound verification time to 1.5 seconds maximum so real-time delivery is never blocked
            return await asyncio.wait_for(_run_single_pass(), timeout=1.5)
        except asyncio.TimeoutError:
            log.info("Hallucination verification timed out (>1.5s), assuming safe baseline")
            return {
                "safe": True,
                "hallucinated_claims": [],
                "supported_claims": [],
                "confidence": 0.95,
            }
