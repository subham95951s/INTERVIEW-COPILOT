import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.job_description import JobDescription
from app.models.user import User
from app.routers.auth import get_current_user_or_dev
from app.services.rag import RAGService

log = structlog.get_logger()
router = APIRouter()


class JDSubmission(BaseModel):
    """Request body for job description submission."""
    raw_text: str
    company: str | None = None
    role: str | None = None


@router.post("/")
async def submit_jd(
    body: JDSubmission,
    current_user: User = Depends(get_current_user_or_dev),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Submit a job description, embed chunks,
    and store in pgvector for RAG retrieval.
    """
    if not body.raw_text.strip():
        raise HTTPException(status_code=400, detail="Job description text is empty.")

    # Create JD record
    jd = JobDescription(
        user_id=current_user.id,
        company=body.company,
        role=body.role,
        raw_text=body.raw_text,
    )
    db.add(jd)
    await db.flush()

    # Parse and embed
    rag = RAGService(db)
    try:
        chunk_count = await rag.ingest_jd(
            user_id=current_user.id,
            document_id=jd.id,
            jd_text=body.raw_text,
        )
    except Exception as e:
        log.error("JD embedding failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to process job description.")

    log.info(
        "JD submitted and indexed",
        jd_id=jd.id,
        company=body.company,
        role=body.role,
        chunks=chunk_count,
    )

    return {
        "jd_id": jd.id,
        "company": body.company,
        "role": body.role,
        "chunks_indexed": chunk_count,
        "message": f"Job description processed. {chunk_count} chunks indexed.",
    }


@router.get("/")
async def list_jds(
    user_id: str = "dev_user",  # TODO: Replace with JWT auth dependency in Phase 2
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all job descriptions for the current user."""
    from sqlalchemy import select
    result = await db.execute(
        select(JobDescription)
        .where(JobDescription.user_id == user_id)
        .order_by(JobDescription.created_at.desc())
    )
    jds = result.scalars().all()
    return {
        "job_descriptions": [
            {
                "id": j.id,
                "company": j.company,
                "role": j.role,
                "created_at": str(j.created_at),
            }
            for j in jds
        ]
    }
