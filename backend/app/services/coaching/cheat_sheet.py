"""
Cheat Sheet Generator — Instant 3-bullet glanceable cheat sheet (<150ms) for candidate talking points.

Provides candidates under pressure with an immediate executive summary of what to say
before reading the full streamed script.
"""

import asyncio
import json
import re
import structlog
from groq import AsyncGroq
from app.config import get_settings

log = structlog.get_logger()

CHEAT_SHEET_PROMPT = """You are an elite interview coach. Given the interview question and the candidate's background context, generate exactly 3 short, high-impact bullet points (max 8-10 words each) for the candidate to glance at and mention in their answer.

Question: {question}

Candidate Background Context:
{background}

Return ONLY a valid JSON array of exactly 3 string bullets:
["• Highlight project X metric", "• Explain STAR action taken", "• Mention result Y achieved"]"""


class CheatSheetGenerator:
    """Generates instant 3-bullet glanceable cheat sheets alongside answer streaming."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key
        self._client: AsyncGroq | None = None
        if api_key:
            self._client = AsyncGroq(api_key=api_key)

    async def generate_bullets(
        self,
        question: str,
        resume_context: str = "",
        timeout_ms: int = 200,
    ) -> list[str]:
        """
        Generate 3 concise talking-point bullets.
        Uses fast local heuristic fallback if Groq API exceeds timeout_ms to guarantee <200ms delivery.
        """
        if not self._client:
            return self._heuristic_bullets(question, resume_context)

        async def _call_llm() -> list[str]:
            try:
                response = await self._client.chat.completions.create(
                    model="llama3-8b-8192",
                    messages=[
                        {
                            "role": "user",
                            "content": CHEAT_SHEET_PROMPT.format(
                                question=question[:300],
                                background=resume_context[:1200],
                            ),
                        }
                    ],
                    temperature=0.2,
                    max_tokens=80,
                )
                content = response.choices[0].message.content or "[]"
                start_idx = content.find("[")
                end_idx = content.rfind("]")
                if start_idx != -1 and end_idx != -1:
                    parsed = json.loads(content[start_idx : end_idx + 1])
                    if isinstance(parsed, list) and len(parsed) >= 2:
                        return [str(b).strip() for b in parsed[:3]]
                return self._heuristic_bullets(question, resume_context)
            except Exception as e:
                log.debug("Cheat sheet LLM fallback", error=str(e))
                return self._heuristic_bullets(question, resume_context)

        try:
            return await asyncio.wait_for(_call_llm(), timeout=timeout_ms / 1000.0)
        except asyncio.TimeoutError:
            log.debug("Cheat sheet generation timed out, returning instant heuristic bullets")
            return self._heuristic_bullets(question, resume_context)

    def _heuristic_bullets(self, question: str, resume_context: str) -> list[str]:
        """Instant <1ms heuristic bullet generation based on question keywords and background."""
        q_lower = question.lower()
        bullets = []

        # Extract up to 2 capitalized project/tool names from context
        projects = re.findall(r"\b([A-Z][a-zA-Z0-9_-]{2,15})\b", resume_context)
        exclusion_set = {
            "resume", "general", "candidate", "project", "projects", "experience",
            "skills", "summary", "education", "work", "history", "company", "role",
            "date", "description", "details", "university", "college", "school",
            "degree", "bachelor", "master", "phd", "pdf", "docx", "http", "https",
            "january", "february", "march", "april", "may", "june", "july",
            "august", "september", "october", "november", "december"
        }
        unique_projects = []
        for p in projects:
            if p.lower() not in exclusion_set and p not in unique_projects:
                unique_projects.append(p)

        if "conflict" in q_lower or "disagreement" in q_lower or "team" in q_lower:
            bullets.append("• State situation clearly & objectively")
            bullets.append("• Focus on collaborative resolution & listening")
            bullets.append("• Highlight positive shared outcome")
        elif "design" in q_lower or "scale" in q_lower or "architecture" in q_lower:
            bullets.append("• Clarify functional & non-functional requirements")
            if unique_projects:
                bullets.append(f"• Reference architecture patterns from {unique_projects[0]}")
            else:
                bullets.append("• Break down core components & bottlenecks")
            bullets.append("• Quantify scalability & tradeoff decisions")
        else:
            if unique_projects:
                bullets.append(f"• Anchor answer with {unique_projects[0]} project experience")
            else:
                bullets.append("• Lead with a strong direct statement")
            bullets.append("• Outline specific actions & ownership taken")
            bullets.append("• Conclude with concrete metrics & results")

        return bullets[:3]
