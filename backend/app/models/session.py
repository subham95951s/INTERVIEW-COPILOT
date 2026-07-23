import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class InterviewSession(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False
    )
    resume_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("resumes.id"), nullable=True
    )
    jd_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("job_descriptions.id"), nullable=True
    )
    mode: Mapped[str] = mapped_column(String, default="mock")
    interview_type: Mapped[str] = mapped_column(String, default="behavioral")
    status: Mapped[str] = mapped_column(String, default="active")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
