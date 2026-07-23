import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.database import Base

# 384 dimensions for all-MiniLM-L6-v2 (fastembed default)
EMBEDDING_DIM = 384


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    document_id: Mapped[str] = mapped_column(
        String, nullable=False, index=True
    )  # resume.id or job_description.id
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False, index=True
    )
    source_type: Mapped[str] = mapped_column(String)  # "resume" | "jd"
    section: Mapped[str | None] = mapped_column(String, nullable=True)
    chunk_text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM))
    # Parent-child chunking (Phase C)
    parent_id: Mapped[str | None] = mapped_column(
        String, nullable=True, index=True
    )
    is_parent: Mapped[bool] = mapped_column(
        default=False, server_default="false"
    )
    parent_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
