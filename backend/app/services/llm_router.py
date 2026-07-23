from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass

import structlog
from groq import AsyncGroq, RateLimitError
from openai import AsyncOpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.config import get_settings

log = structlog.get_logger()
settings = get_settings()

ANSWER_SYSTEM_PROMPT = """You are helping {candidate_name} answer an interview question in real-time.

RULES:
- Respond in FIRST PERSON ("I") immediately as the candidate speaking in the interview
- Be concise, confident, and natural: 100-150 words for behavioral/technical questions
- Use STAR format (Situation, Task, Action, Result) for behavioral questions
- Ground your answers in the candidate's actual background below where applicable
- NEVER use disclaimers, apologies, or meta-phrases such as "As someone without a specified background in...", "While my resume doesn't mention...", or "I would say..."
- If asked about a topic not explicitly detailed in your background, answer confidently using fundamental engineering principles, general best practices, or transferable skills without apologizing or calling out the gap

## Candidate Background (from their resume):
{rag_chunks}

## Job Description Highlights:
{jd_summary}

## Recent Conversation Context:
{conversation_history}
"""

USER_PROMPT_TEMPLATE = """Interview Question: {question}

Provide a strong, personalized answer based on the candidate's background above."""


@dataclass
class LLMContext:
    candidate_name: str
    rag_chunks: str
    jd_summary: str
    conversation_history: str
    question: str


class LLMProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    async def generate_stream(
        self,
        context: LLMContext,
    ) -> AsyncGenerator[str, None]:
        """Yield tokens as they are generated."""
        ...


class GroqProvider(LLMProvider):
    """
    Groq Llama-3.3-70B — fastest inference for real-time UX.
    Target TTFT: < 400ms.
    Rate limit handling with exponential backoff (fix.md Gap 2.5).
    """

    def __init__(self) -> None:
        self.client = AsyncGroq(api_key=settings.groq_api_key)

    @retry(
        retry=retry_if_exception_type(RateLimitError),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=2, min=1, max=30),
    )
    async def generate_stream(
        self,
        context: LLMContext,
    ) -> AsyncGenerator[str, None]:
        system_prompt = ANSWER_SYSTEM_PROMPT.format(
            candidate_name=context.candidate_name,
            rag_chunks=context.rag_chunks,
            jd_summary=context.jd_summary,
            conversation_history=context.conversation_history,
        )

        stream = await self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": USER_PROMPT_TEMPLATE.format(
                    question=context.question
                )},
            ],
            temperature=0.7,
            max_tokens=300,
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


class OpenAIProvider(LLMProvider):
    """
    OpenAI GPT-4o — higher quality, used for mock mode or when user opts in.
    """

    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def generate_stream(
        self,
        context: LLMContext,
    ) -> AsyncGenerator[str, None]:
        system_prompt = ANSWER_SYSTEM_PROMPT.format(
            candidate_name=context.candidate_name,
            rag_chunks=context.rag_chunks,
            jd_summary=context.jd_summary,
            conversation_history=context.conversation_history,
        )

        stream = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": USER_PROMPT_TEMPLATE.format(
                    question=context.question
                )},
            ],
            temperature=0.7,
            max_tokens=300,
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


class NvidiaProvider(LLMProvider):
    """
    NVIDIA API (e.g., GLM 5.2) — OpenAI compatible endpoint.
    """

    def __init__(self) -> None:
        self.client = AsyncOpenAI(
            api_key=settings.nvidia_api_key,
            base_url="https://integrate.api.nvidia.com/v1"
        )

    async def generate_stream(
        self,
        context: LLMContext,
    ) -> AsyncGenerator[str, None]:
        system_prompt = ANSWER_SYSTEM_PROMPT.format(
            candidate_name=context.candidate_name,
            rag_chunks=context.rag_chunks,
            jd_summary=context.jd_summary,
            conversation_history=context.conversation_history,
        )

        stream = await self.client.chat.completions.create(
            model=settings.nvidia_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": USER_PROMPT_TEMPLATE.format(
                    question=context.question
                )},
            ],
            temperature=0.7,
            max_tokens=300,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


def get_llm_provider(provider: str | None = None) -> LLMProvider:
    """Factory function — returns the configured LLM provider."""
    target = provider or settings.llm_provider
    if target == "groq":
        return GroqProvider()
    elif target == "openai":
        return OpenAIProvider()
    elif target == "nvidia":
        return NvidiaProvider()
    else:
        raise ValueError(f"Unknown LLM provider: {target}")
