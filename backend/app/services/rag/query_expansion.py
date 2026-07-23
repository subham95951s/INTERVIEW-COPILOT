"""
Query expansion improves retrieval by generating multiple
search queries from one interview question.

Uses Groq llama3-8b-8192 (fast, free-tier) to expand a single
question into 3 additional search queries that target different
aspects of the question.

Example:
  Original: "Tell me about leading a project"
  Expanded:
    - "project leadership experience"
    - "team management software development"
    - "cross-functional team coordination"
"""

import json

import structlog
from groq import AsyncGroq, RateLimitError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.config import get_settings

log = structlog.get_logger()

EXPANSION_PROMPT = """Given this interview question, generate 3 alternative search queries \
to find relevant experience in a resume. Each query should be short (5-8 words) \
and focus on different aspects of the question.

Question: {question}

Return ONLY a valid JSON array of strings, nothing else:
["query 1", "query 2", "query 3"]"""


class QueryExpander:
    """
    Generates alternative search queries from an interview question
    to improve retrieval recall across BM25 and vector search.
    """

    def __init__(self, client: AsyncGroq | None = None) -> None:
        if client is None:
            settings = get_settings()
            self.client = AsyncGroq(api_key=settings.groq_api_key)
        else:
            self.client = client

    @retry(
        retry=retry_if_exception_type(RateLimitError),
        stop=stop_after_attempt(2),
        wait=wait_exponential(min=1, max=5),
    )
    async def expand(self, question: str) -> list[str]:
        """
        Generate alternative search queries for better retrieval.

        Args:
            question: The original interview question.

        Returns:
            List of queries: [original] + up to 3 expanded queries.
            On any error, returns [original] only (graceful degradation).
        """
        try:
            response = await self.client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[{
                    "role": "user",
                    "content": EXPANSION_PROMPT.format(question=question),
                }],
                temperature=0.3,
                max_tokens=100,
            )

            content = response.choices[0].message.content or ""
            # Try to extract JSON array from response
            parsed = self._parse_json_array(content)

            if parsed:
                expanded = [question] + parsed[:3]
                log.debug(
                    "Query expanded",
                    original=question[:60],
                    expansions=parsed[:3],
                )
                return expanded

            return [question]

        except RateLimitError:
            raise  # Let tenacity retry this
        except Exception as e:
            log.warning(
                "Query expansion failed, using original query only",
                error=str(e),
            )
            return [question]

    @staticmethod
    def _parse_json_array(content: str) -> list[str] | None:
        """
        Parse a JSON array from LLM response, handling common formatting issues.
        """
        content = content.strip()

        # Try direct parse
        try:
            result = json.loads(content)
            if isinstance(result, list) and all(isinstance(x, str) for x in result):
                return result
        except json.JSONDecodeError:
            pass

        # Try extracting array from markdown code block
        import re
        match = re.search(r'\[.*?\]', content, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
                if isinstance(result, list) and all(isinstance(x, str) for x in result):
                    return result
            except json.JSONDecodeError:
                pass

        return None
