import json
import time
import structlog
import redis.asyncio as aioredis

from app.config import get_settings

log = structlog.get_logger()
settings = get_settings()

SESSION_TTL_SECONDS = settings.max_session_duration_hours * 3600
TRANSCRIPT_BUFFER_SECONDS = 30
MAX_QA_HISTORY = 5


class SessionManager:
    """
    Redis-backed session state manager.
    Handles transcript buffer, Q&A history, session metadata,
    and ingestion status tracking (fix.md Gap 2.4).
    """

    def __init__(self, redis: aioredis.Redis) -> None:
        self.redis = redis

    # ── Keys ─────────────────────────────────────────────────────────

    def _transcript_key(self, session_id: str) -> str:
        return f"session:{session_id}:transcript_buffer"

    def _qa_key(self, session_id: str) -> str:
        return f"session:{session_id}:qa_history"

    def _status_key(self, session_id: str) -> str:
        return f"session:{session_id}:status"

    def _meta_key(self, session_id: str) -> str:
        return f"session:{session_id}:meta"

    def _ingestion_key(self, session_id: str) -> str:
        return f"session:{session_id}:ingestion_status"

    # ── Session Lifecycle ─────────────────────────────────────────────

    async def create_session(
        self,
        session_id: str,
        user_id: str,
        candidate_name: str,
    ) -> None:
        meta = {
            "user_id": user_id,
            "candidate_name": candidate_name,
            "created_at": str(time.time()),
        }
        pipe = self.redis.pipeline()
        pipe.set(self._status_key(session_id), "active", ex=SESSION_TTL_SECONDS)
        pipe.hset(self._meta_key(session_id), mapping=meta)
        pipe.expire(self._meta_key(session_id), SESSION_TTL_SECONDS)
        await pipe.execute()
        log.info("Session created in Redis", session_id=session_id)

    async def end_session(self, session_id: str) -> None:
        await self.redis.set(self._status_key(session_id), "ended")

    async def get_status(self, session_id: str) -> str | None:
        return await self.redis.get(self._status_key(session_id))

    async def get_meta(self, session_id: str) -> dict:
        return await self.redis.hgetall(self._meta_key(session_id))

    # ── Ingestion Status (fix.md Gap 2.4) ─────────────────────────────

    async def set_ingestion_status(
        self,
        session_id: str,
        status: str,
        chunks_indexed: int = 0,
    ) -> None:
        """Set ingestion status: 'pending' | 'ready' | 'failed'"""
        data = json.dumps({"status": status, "chunks_indexed": chunks_indexed})
        await self.redis.set(
            self._ingestion_key(session_id),
            data,
            ex=SESSION_TTL_SECONDS,
        )

    async def get_ingestion_status(self, session_id: str) -> dict:
        raw = await self.redis.get(self._ingestion_key(session_id))
        if raw:
            return json.loads(raw)
        return {"status": "pending", "chunks_indexed": 0}

    # ── Transcript Buffer ─────────────────────────────────────────────

    async def append_transcript(
        self,
        session_id: str,
        speaker: str,
        text: str,
        timestamp_ms: int,
    ) -> None:
        entry = json.dumps({
            "speaker": speaker,
            "text": text,
            "timestamp_ms": timestamp_ms,
        })
        key = self._transcript_key(session_id)
        pipe = self.redis.pipeline()
        pipe.rpush(key, entry)
        pipe.expire(key, SESSION_TTL_SECONDS)
        await pipe.execute()

    async def get_recent_transcript(
        self,
        session_id: str,
        seconds: int = 30,
    ) -> str:
        """Get the last N seconds of transcript as a formatted string."""
        key = self._transcript_key(session_id)
        entries_raw = await self.redis.lrange(key, -60, -1)

        if not entries_raw:
            return ""

        cutoff_ms = (time.time() - seconds) * 1000
        lines = []
        for raw in entries_raw:
            entry = json.loads(raw)
            if entry["timestamp_ms"] >= cutoff_ms:
                speaker_label = (
                    "Interviewer" if entry["speaker"] == "0" else "Candidate"
                )
                lines.append(f"{speaker_label}: {entry['text']}")

        return "\n".join(lines)

    # ── Q&A History ───────────────────────────────────────────────────

    async def append_qa(
        self,
        session_id: str,
        question: str,
        answer: str,
    ) -> None:
        entry = json.dumps({"question": question, "answer": answer})
        key = self._qa_key(session_id)
        pipe = self.redis.pipeline()
        pipe.rpush(key, entry)
        # Keep only last MAX_QA_HISTORY entries
        pipe.ltrim(key, -MAX_QA_HISTORY, -1)
        pipe.expire(key, SESSION_TTL_SECONDS)
        await pipe.execute()

    async def get_qa_history(self, session_id: str) -> str:
        """Format Q&A history as context string for LLM prompt."""
        key = self._qa_key(session_id)
        entries_raw = await self.redis.lrange(key, 0, -1)

        if not entries_raw:
            return "No previous exchanges."

        lines = []
        for raw in entries_raw:
            entry = json.loads(raw)
            lines.append(f"Q: {entry['question']}\nA: {entry['answer']}")

        return "\n\n".join(lines)
