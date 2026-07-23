import json
import structlog
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.resume import Resume
from app.models.user import User
from app.routers.auth import get_current_user_or_dev
from app.services.rag import RAGService

log = structlog.get_logger()
router = APIRouter()

ALLOWED_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/")
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_or_dev),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Upload a resume (PDF or DOCX), parse it, embed chunks,
    and store in pgvector for RAG retrieval.
    """
    # Validate file type
    content_type = file.content_type or ""
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {content_type}. Use PDF or DOCX.",
        )

    file_type = ALLOWED_TYPES[content_type]

    # Read and validate file size
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)} MB.",
        )

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")

    # Create resume record
    rag = RAGService(db)

    try:
        chunk_count, raw_text = await rag.ingest_resume(
            user_id=current_user.id,
            document_id="",  # Will be set after resume record creation
            file_bytes=file_bytes,
            file_type=file_type,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error("Resume parsing/embedding failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to process resume.")

    # Store resume record
    resume = Resume(
        user_id=current_user.id,
        filename=file.filename or "unknown",
        raw_text=raw_text,
    )
    db.add(resume)
    await db.flush()

    # Update document_id on chunks to point to this resume
    from sqlalchemy import update
    from app.models.document_chunk import DocumentChunk
    await db.execute(
        update(DocumentChunk)
        .where(DocumentChunk.document_id == "")
        .where(DocumentChunk.user_id == current_user.id)
        .values(document_id=resume.id)
    )

    log.info(
        "Resume uploaded and indexed",
        resume_id=resume.id,
        filename=file.filename,
        chunks=chunk_count,
    )

    return {
        "resume_id": resume.id,
        "filename": file.filename,
        "chunks_indexed": chunk_count,
        "message": f"Resume processed successfully. {chunk_count} chunks indexed.",
    }


@router.get("/")
async def list_resumes(
    user_id: str = "dev_user",  # TODO: Replace with JWT auth dependency in Phase 2
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all resumes for the current user."""
    from sqlalchemy import select
    result = await db.execute(
        select(Resume)
        .where(Resume.user_id == user_id)
        .order_by(Resume.created_at.desc())
    )
    resumes = result.scalars().all()
    return {
        "resumes": [
            {
                "id": r.id,
                "filename": r.filename,
                "created_at": str(r.created_at),
            }
            for r in resumes
        ]
    }
