"""
Cross-Session Persistent Memory for Interview History & Progression Tracking.
Stores and retrieves historical session performance summaries from PostgreSQL.
"""

import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.session_summary import SessionSummary
import structlog

log = structlog.get_logger()


class CrossSessionMemory:
    """
    Persistent memory across multiple interview sessions.
    Enables learning from past performance and personalizing future coaching.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_user_performance_context(self, user_id: str, limit: int = 5) -> str:
        """
        Get summary of user's past interview performance.
        Used to personalize coaching for the current session.
        """
        try:
            stmt = (
                select(SessionSummary)
                .where(SessionSummary.user_id == user_id)
                .order_by(SessionSummary.started_at.desc())
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            rows = result.scalars().all()

            if not rows:
                return "No previous session history."

            summaries = []
            for row in rows:
                clarity = f"{row.clarity_score:.1f}/10" if row.clarity_score is not None else "N/A"
                structure = f"{row.structure_score:.1f}/10" if row.structure_score is not None else "N/A"
                date_str = row.started_at.strftime("%Y-%m-%d") if row.started_at else "Recent"
                summaries.append(
                    f"- Session ({date_str}, {row.interview_type}): Clarity={clarity}, Structure={structure}"
                )

            return (
                "User's historical interview performance:\n"
                + "\n".join(summaries)
                + "\n\nFocus on helping them improve clarity and structure."
            )
        except Exception as e:
            log.warning("Failed to fetch cross-session memory context", error=str(e))
            return "No previous session history."

    async def identify_weak_areas(self, user_id: str) -> list[str]:
        """Identify consistent weak areas across recent sessions."""
        try:
            stmt = (
                select(SessionSummary)
                .where(SessionSummary.user_id == user_id)
                .order_by(SessionSummary.started_at.desc())
                .limit(10)
            )
            result = await self.db.execute(stmt)
            rows = result.scalars().all()

            if not rows:
                return []

            clarities = [r.clarity_score for r in rows if r.clarity_score is not None]
            structures = [r.structure_score for r in rows if r.structure_score is not None]

            weak_areas = []
            if clarities and sum(clarities) / len(clarities) < 6.5:
                weak_areas.append("answer_clarity")
            if structures and sum(structures) / len(structures) < 6.5:
                weak_areas.append("star_structure")

            return weak_areas
        except Exception as e:
            log.warning("Failed to identify weak areas", error=str(e))
            return []

    async def record_session_summary(
        self,
        session_id: str,
        user_id: str,
        interview_type: str = "behavioral",
        total_questions: int = 0,
        clarity_score: float | None = None,
        structure_score: float | None = None,
        topics_covered: list[str] | None = None,
        weak_areas: list[str] | None = None,
    ) -> SessionSummary:
        """Persist session summary to PostgreSQL."""
        summary = SessionSummary(
            session_id=session_id,
            user_id=user_id,
            interview_type=interview_type,
            total_questions=total_questions,
            clarity_score=clarity_score,
            structure_score=structure_score,
            topics_covered=json.dumps(topics_covered or []),
            weak_areas=json.dumps(weak_areas or []),
        )
        self.db.add(summary)
        await self.db.commit()
        await self.db.refresh(summary)
        return summary
