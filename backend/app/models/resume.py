import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_sections: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON string of section→text mapping
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
