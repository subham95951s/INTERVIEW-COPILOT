import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Float, Integer, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class SessionSummary(Base):
    __tablename__ = "session_summaries"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String, ForeignKey("sessions.id"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False
    )
    interview_type: Mapped[str] = mapped_column(String, default="behavioral")
    total_questions: Mapped[int] = mapped_column(Integer, default=0)
    clarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    structure_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    topics_covered: Mapped[str] = mapped_column(String, default="[]")
    weak_areas: Mapped[str] = mapped_column(String, default="[]")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
