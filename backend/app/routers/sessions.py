from datetime import datetime, timezone
import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.session import InterviewSession
from app.models.user import User
from app.routers.auth import get_current_user_or_dev

log = structlog.get_logger()
router = APIRouter()


class CreateSessionRequest(BaseModel):
    mode: str = "mock"
    interview_type: str = "behavioral"
    resume_id: str | None = None
    jd_id: str | None = None


class SessionResponse(BaseModel):
    id: str
    user_id: str
    mode: str
    interview_type: str
    status: str
    resume_id: str | None = None
    jd_id: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None

    class Config:
        from_attributes = True


@router.post("/", response_model=SessionResponse)
async def create_session(
    body: CreateSessionRequest,
    current_user: User = Depends(get_current_user_or_dev),
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """Create a new interview session."""
    session = InterviewSession(
        user_id=current_user.id,
        mode=body.mode,
        interview_type=body.interview_type,
        resume_id=body.resume_id,
        jd_id=body.jd_id,
        status="active",
    )
    db.add(session)
    await db.flush()

    log.info("Created session", session_id=session.id, user_id=current_user.id)
    return SessionResponse.model_validate(session)


@router.get("/", response_model=list[SessionResponse])
async def list_sessions(
    current_user: User = Depends(get_current_user_or_dev),
    db: AsyncSession = Depends(get_db),
) -> list[SessionResponse]:
    """List sessions for the current user."""
    result = await db.execute(
        select(InterviewSession)
        .where(InterviewSession.user_id == current_user.id)
        .order_by(InterviewSession.started_at.desc())
    )
    sessions = result.scalars().all()
    return [SessionResponse.model_validate(s) for s in sessions]


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user_or_dev),
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """Get details of a specific session."""
    result = await db.execute(
        select(InterviewSession).where(
            InterviewSession.id == session_id,
            InterviewSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionResponse.model_validate(session)


@router.patch("/{session_id}/end", response_model=SessionResponse)
async def end_session(
    session_id: str,
    current_user: User = Depends(get_current_user_or_dev),
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """Mark a session as ended."""
    result = await db.execute(
        select(InterviewSession).where(
            InterviewSession.id == session_id,
            InterviewSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.status = "ended"
    session.ended_at = datetime.now(timezone.utc)
    await db.flush()
    return SessionResponse.model_validate(session)
