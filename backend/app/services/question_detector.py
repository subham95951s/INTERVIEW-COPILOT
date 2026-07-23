import json
import structlog
from dataclasses import dataclass
from groq import AsyncGroq, RateLimitError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.config import get_settings

log = structlog.get_logger()
settings = get_settings()

CLASSIFIER_PROMPT = """Analyze this interview transcript snippet.
Determine if the transcript ends with a COMPLETE interview question directed at the candidate that requires a substantive answer.

Return ONLY valid JSON matching this exact schema:
{{
  "is_question": boolean,
  "confidence": float between 0 and 1,
  "cleaned_question": string or null,
  "question_type": "behavioral" | "technical" | "system_design" | "coding" | "small_talk" | null
}}

CRITICAL RULES:
1. "is_question" MUST BE FALSE if the snippet is merely setting up a scenario, premise, or background context (e.g. "Imagine you're designing a distributed serving infrastructure..." or "Let's say we have a service...") without asking what to do yet.
2. "is_question" MUST BE FALSE if the snippet is an incomplete sentence fragment or mid-thought (e.g. "Could you tell us about the recent" or "Identify areas where simplification").
3. "is_question" MUST BE FALSE if the speaker is answering a question or making a statement.
4. "is_question" MUST ONLY BE TRUE when the interviewer has finished asking the complete question or prompt.
5. If "is_question" is true, "cleaned_question" MUST be the complete, unified question incorporating the relevant premise/context from the transcript.
6. "is_question" MUST BE FALSE for meta-questions, small talk, navigation prompts, or interview transitions (e.g. "Should we proceed to another term?", "Ready to continue?", "Let's move on", "Next question", "Is there something specific you'd like to discuss?").

Transcript:
{transcript}"""


@dataclass
class QuestionDetectionResult:
    is_question: bool
    confidence: float
    cleaned_question: str | None
    question_type: str | None


class QuestionDetector:
    """
    Uses Groq Llama-3-8B to classify whether a transcript
    snippet contains an interview question directed at the candidate.
    Target latency: < 150ms

    Rate limit handling with exponential backoff (fix.md Gap 2.5).
    """

    def __init__(self) -> None:
        self.client = AsyncGroq(api_key=settings.groq_api_key)

    @retry(
        retry=retry_if_exception_type(RateLimitError),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=2, min=1, max=30),
    )
    async def classify(
        self,
        transcript_buffer: str,
    ) -> QuestionDetectionResult:
        """
        Classify whether the transcript buffer ends with an interview question.
        Retries on Groq rate limits with exponential backoff.
        """
        try:
            response = await self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {
                        "role": "user",
                        "content": CLASSIFIER_PROMPT.format(
                            transcript=transcript_buffer
                        ),
                    }
                ],
                temperature=0.1,
                max_tokens=150,
                response_format={"type": "json_object"},
            )

            raw = response.choices[0].message.content
            parsed = json.loads(raw)

            return QuestionDetectionResult(
                is_question=parsed.get("is_question", False),
                confidence=float(parsed.get("confidence", 0.0)),
                cleaned_question=parsed.get("cleaned_question"),
                question_type=parsed.get("question_type"),
            )

        except json.JSONDecodeError as e:
            log.warning("Question detector JSON parse error", error=str(e))
            return QuestionDetectionResult(
                is_question=False,
                confidence=0.0,
                cleaned_question=None,
                question_type=None,
            )
        except RateLimitError:
            log.warning("Groq rate limit hit on question detector, retrying...")
            raise  # Let tenacity handle retry
        except Exception as e:
            log.error("Question detector error", error=str(e))
            raise
