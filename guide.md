InterviewCopilot AI — Complete Implementation Guide
Built with Antigravity | Full Codebase, File by File
Pre-Flight: Antigravity Project Setup
Before writing a single line of code, configure Antigravity with the full context so every agent mission has the same source of truth.

Markdown

# .antigravity/PROJECT_CONTEXT.md
# This file is auto-loaded by Antigravity at the start of every mission.
# Do not delete or rename.

## Project: InterviewCopilot AI
## Repo root: e:\IC\
## Active phase: Phase 0

## Non-negotiable rules for every agent mission:
1. Never hardcode API keys. Always read from .env via config.py
2. All Python code must use async/await. No blocking calls in event loops.
3. All Python functions must have type hints. All Pydantic models must be explicit.
4. Folder structure is fixed per PROJECT_BRIEF.md. Do not deviate.
5. Every mission ends with a verification step using the browser tool or terminal.
6. Run `pytest` before marking any backend mission complete.
7. Run `npm run build` before marking any frontend mission complete.

## Current decisions (resolved):
- Auth: Custom JWT (no Clerk dependency for MVP)
- Hosting: Docker Compose local → Fly.io production
- Embeddings: OpenAI text-embedding-3-small
- Mock interviewer voice: OpenAI TTS (gpt-4o-mini-tts) for MVP
- Pricing: Credits + 60-day pass (implemented in Phase 2)
- Repo: Monorepo at e:\IC\

## API Keys needed (check .env before starting any mission):
- DEEPGRAM_API_KEY
- GROQ_API_KEY
- OPENAI_API_KEY
- DATABASE_URL
- REDIS_URL
- JWT_SECRET_KEY
Phase 0 — Core Pipeline Validation
Mission 0.1 — Project Scaffold
docker-compose.yml
YAML

version: "3.9"

services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: ic_postgres
    environment:
      POSTGRES_USER: ic_user
      POSTGRES_PASSWORD: ic_password
      POSTGRES_DB: interviewcopilot
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/scripts/init_db.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ic_user -d interviewcopilot"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: ic_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: ic_backend
    environment:
      - DATABASE_URL=postgresql+asyncpg://ic_user:ic_password@postgres:5432/interviewcopilot
      - REDIS_URL=redis://redis:6379
    env_file:
      - .env
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

volumes:
  postgres_data:
  redis_data:
.env.example
Bash

# ─── API Keys ──────────────────────────────────────────────
DEEPGRAM_API_KEY=your_deepgram_api_key_here
GROQ_API_KEY=your_groq_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# ─── Database ──────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://ic_user:ic_password@localhost:5432/interviewcopilot

# ─── Redis ─────────────────────────────────────────────────
REDIS_URL=redis://localhost:6379

# ─── Auth ──────────────────────────────────────────────────
JWT_SECRET_KEY=your_super_secret_jwt_key_change_this_in_production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# ─── Provider Selection ────────────────────────────────────
STT_PROVIDER=deepgram           # deepgram | whisper
LLM_PROVIDER=groq               # groq | openai | anthropic
EMBEDDING_MODEL=text-embedding-3-small

# ─── App Config ────────────────────────────────────────────
ENVIRONMENT=development          # development | production
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
MAX_SESSION_DURATION_HOURS=4
VAD_SILENCE_THRESHOLD_MS=1000
QUESTION_CONFIDENCE_THRESHOLD=0.7
backend/scripts/init_db.sql
SQL

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Verify extensions loaded
DO $$
BEGIN
  RAISE NOTICE 'Extensions loaded: vector, uuid-ossp';
END $$;
backend/requirements.txt
txt

# ─── Core Framework ────────────────────────────────────────
fastapi==0.115.0
uvicorn[standard]==0.30.6
websockets==13.0
python-multipart==0.0.9
python-dotenv==1.0.1
pydantic==2.9.0
pydantic-settings==2.5.2
email-validator==2.2.0

# ─── Database ──────────────────────────────────────────────
sqlalchemy[asyncio]==2.0.35
asyncpg==0.29.0
alembic==1.13.3
pgvector==0.3.2

# ─── Redis ─────────────────────────────────────────────────
redis[hiredis]==5.1.0

# ─── Auth ──────────────────────────────────────────────────
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# ─── STT ───────────────────────────────────────────────────
deepgram-sdk==3.7.0

# ─── AI / ML ───────────────────────────────────────────────
groq==0.11.0
openai==1.51.0
httpx==0.27.2
anthropic==0.34.2

# ─── VAD ───────────────────────────────────────────────────
silero-vad==5.1
torch==2.4.1
torchaudio==2.4.1
numpy==2.1.1

# ─── Document Parsing ──────────────────────────────────────
pdfplumber==0.11.4
python-docx==1.1.2

# ─── Utilities ─────────────────────────────────────────────
aiofiles==24.1.0
structlog==24.4.0
tenacity==9.0.0

# ─── Testing ───────────────────────────────────────────────
pytest==8.3.3
pytest-asyncio==0.24.0
pytest-mock==3.14.0
httpx==0.27.2
backend/Dockerfile
Dockerfile

FROM python:3.12-slim

WORKDIR /app

# System dependencies for audio processing
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libsndfile1 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
Mission 0.2 — Backend Core
backend/app/config.py
Python

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # API Keys
    deepgram_api_key: str
    groq_api_key: str
    openai_api_key: str

    # Database
    database_url: str

    # Redis
    redis_url: str

    # Auth
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 30

    # Provider Selection
    stt_provider: str = "deepgram"
    llm_provider: str = "groq"
    embedding_model: str = "text-embedding-3-small"

    # App Config
    environment: str = "development"
    cors_origins: str = "http://localhost:5173"
    max_session_duration_hours: int = 4
    vad_silence_threshold_ms: int = 1000
    question_confidence_threshold: float = 0.7

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
backend/app/database.py
Python

from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
backend/app/main.py
Python

import structlog
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.routers import auth, resumes, job_descriptions, sessions, websocket

log = structlog.get_logger()
settings = get_settings()

# Global Redis client
redis_client: aioredis.Redis | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize and cleanup application resources."""
    global redis_client

    log.info("Starting InterviewCopilot AI backend")

    # Initialize database
    await init_db()
    log.info("Database initialized")

    # Initialize Redis
    redis_client = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
    await redis_client.ping()
    log.info("Redis connected")

    # Store on app state for dependency injection
    app.state.redis = redis_client

    yield

    # Cleanup
    if redis_client:
        await redis_client.aclose()
    log.info("Backend shutdown complete")


app = FastAPI(
    title="InterviewCopilot AI",
    version="1.0.0",
    description="Real-time AI interview coaching platform",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(resumes.router, prefix="/resumes", tags=["resumes"])
app.include_router(
    job_descriptions.router,
    prefix="/job-descriptions",
    tags=["job-descriptions"],
)
app.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
app.include_router(websocket.router, tags=["websocket"])


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy", "version": "1.0.0"}
Mission 0.3 — STT Service
backend/app/services/stt/base.py
Python

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass


@dataclass
class TranscriptEvent:
    text: str
    is_final: bool
    speaker: str | None  # "0", "1", etc. from diarization
    confidence: float
    timestamp_ms: int


class STTProvider(ABC):
    """Abstract interface for Speech-to-Text providers."""

    @abstractmethod
    async def stream_audio(
        self,
        audio_stream: AsyncGenerator[bytes, None],
    ) -> AsyncGenerator[TranscriptEvent, None]:
        """
        Accepts a stream of raw PCM audio bytes.
        Yields TranscriptEvent objects as speech is recognized.
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """Clean up connections and resources."""
        ...
backend/app/services/stt/deepgram.py
Python

import time
import structlog
from collections.abc import AsyncGenerator
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
)
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.services.stt.base import STTProvider, TranscriptEvent

log = structlog.get_logger()
settings = get_settings()


class DeepgramProvider(STTProvider):
    """
    Deepgram streaming STT with diarization.
    Uses nova-2 model for best accuracy/latency tradeoff.
    """

    def __init__(self) -> None:
        self.client = DeepgramClient(
            settings.deepgram_api_key,
            config=DeepgramClientOptions(verbose=False),
        )

    async def stream_audio(
        self,
        audio_stream: AsyncGenerator[bytes, None],
    ) -> AsyncGenerator[TranscriptEvent, None]:
        """Stream audio to Deepgram, yield transcript events."""

        # Queue to bridge callback-based Deepgram SDK to async generator
        import asyncio
        queue: asyncio.Queue[TranscriptEvent | None] = asyncio.Queue()

        connection = self.client.listen.asynclive.v("1")

        @connection.on(LiveTranscriptionEvents.Transcript)
        async def on_transcript(self_inner, result, **kwargs):  # type: ignore
            try:
                alt = result.channel.alternatives[0]
                if not alt.transcript:
                    return

                speaker = None
                if alt.words and hasattr(alt.words[0], "speaker"):
                    speaker = str(alt.words[0].speaker)

                event = TranscriptEvent(
                    text=alt.transcript,
                    is_final=result.is_final,
                    speaker=speaker,
                    confidence=alt.confidence,
                    timestamp_ms=int(time.time() * 1000),
                )
                await queue.put(event)
            except Exception as e:
                log.error("Deepgram transcript callback error", error=str(e))

        @connection.on(LiveTranscriptionEvents.Error)
        async def on_error(self_inner, error, **kwargs):  # type: ignore
            log.error("Deepgram error", error=str(error))
            await queue.put(None)  # Signal termination

        options = LiveOptions(
            model="nova-2",
            language="en-US",
            punctuate=True,
            diarize=True,
            interim_results=True,
            endpointing=300,
            smart_format=True,
            sample_rate=16000,
            channels=1,
            encoding="linear16",
        )

        started = await connection.start(options)
        if not started:
            raise RuntimeError("Failed to start Deepgram connection")

        log.info("Deepgram connection established")

        # Feed audio in background task
        import asyncio

        async def feed_audio() -> None:
            try:
                async for chunk in audio_stream:
                    await connection.send(chunk)
            except Exception as e:
                log.error("Audio feed error", error=str(e))
            finally:
                await connection.finish()
                await queue.put(None)  # Signal end

        asyncio.create_task(feed_audio())

        # Yield events from queue
        while True:
            event = await queue.get()
            if event is None:
                break
            yield event

    async def close(self) -> None:
        log.info("Deepgram provider closed")
Mission 0.4 — VAD + Question Detector
backend/app/services/vad.py
Python

import asyncio
import time
import numpy as np
import structlog
import torch
from dataclasses import dataclass, field

log = structlog.get_logger()

# Silero VAD constants
SAMPLE_RATE = 16000
CHUNK_DURATION_MS = 250
CHUNK_SAMPLES = int(SAMPLE_RATE * CHUNK_DURATION_MS / 1000)  # 4000 samples


@dataclass
class VADState:
    is_speaking: bool = False
    silence_start_ms: float | None = None
    speech_buffer: list[bytes] = field(default_factory=list)
    last_speech_ms: float = 0.0


class SileroVAD:
    """
    Silero VAD wrapper for real-time voice activity detection.
    Detects when the speaker stops talking (silence > threshold).
    """

    def __init__(self, silence_threshold_ms: int = 1000) -> None:
        self.silence_threshold_ms = silence_threshold_ms
        self._model: torch.nn.Module | None = None
        self._load_model()

    def _load_model(self) -> None:
        """Load Silero VAD model. Called once at startup."""
        try:
            model, _ = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                force_reload=False,
                onnx=False,
            )
            self._model = model
            self._model.eval()
            log.info("Silero VAD model loaded")
        except Exception as e:
            log.error("Failed to load Silero VAD", error=str(e))
            raise

    def get_speech_probability(self, pcm_bytes: bytes) -> float:
        """
        Get probability that the audio chunk contains speech.
        Input: 250ms of 16kHz mono PCM (int16 bytes)
        Output: float in [0, 1]
        """
        if self._model is None:
            return 0.0

        try:
            audio_array = np.frombuffer(pcm_bytes, dtype=np.int16)
            audio_float = audio_array.astype(np.float32) / 32768.0
            tensor = torch.from_numpy(audio_float)

            with torch.no_grad():
                prob = self._model(tensor, SAMPLE_RATE).item()

            return float(prob)
        except Exception as e:
            log.warning("VAD inference error", error=str(e))
            return 0.0

    def process_chunk(
        self,
        pcm_bytes: bytes,
        state: VADState,
        speech_threshold: float = 0.5,
    ) -> tuple[VADState, bool]:
        """
        Process one audio chunk. Returns updated state and
        whether an end-of-utterance was detected.
        """
        now_ms = time.time() * 1000
        prob = self.get_speech_probability(pcm_bytes)
        end_of_utterance = False

        if prob >= speech_threshold:
            # Speech detected
            state.is_speaking = True
            state.silence_start_ms = None
            state.last_speech_ms = now_ms
            state.speech_buffer.append(pcm_bytes)
        else:
            # Silence detected
            if state.is_speaking:
                if state.silence_start_ms is None:
                    state.silence_start_ms = now_ms

                silence_duration = now_ms - state.silence_start_ms
                if silence_duration >= self.silence_threshold_ms:
                    # End of utterance!
                    end_of_utterance = True
                    state.is_speaking = False
                    state.silence_start_ms = None
                    state.speech_buffer = []

        return state, end_of_utterance
backend/app/services/question_detector.py
Python

import json
import structlog
from dataclasses import dataclass
from groq import AsyncGroq
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings

log = structlog.get_logger()
settings = get_settings()

CLASSIFIER_PROMPT = """Analyze this interview transcript snippet.
Determine if the LAST utterance is a complete interview question 
directed at the candidate that requires a substantive answer.

Return ONLY valid JSON matching this exact schema:
{
  "is_question": boolean,
  "confidence": float between 0 and 1,
  "cleaned_question": string or null,
  "question_type": "behavioral" | "technical" | "system_design" | "coding" | "small_talk" | null
}

Do NOT classify as questions:
- Greetings or small talk ("How are you?", "Can you hear me?")
- Statements or observations
- Interviewer thinking out loud

Transcript:
{transcript}"""


@dataclass
class QuestionDetectionResult:
    is_question: bool
    confidence: float
    cleaned_question: str | None
    question_type: str | None


class QuestionDetector:
    """
    Uses Groq Llama-3-8B to classify whether a transcript 
    snippet contains an interview question directed at the candidate.
    Target latency: < 150ms
    """

    def __init__(self) -> None:
        self.client = AsyncGroq(api_key=settings.groq_api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=0.1, max=1),
    )
    async def classify(
        self,
        transcript_buffer: str,
    ) -> QuestionDetectionResult:
        """
        Classify whether the transcript buffer ends with an interview question.
        """
        try:
            response = await self.client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {
                        "role": "user",
                        "content": CLASSIFIER_PROMPT.format(
                            transcript=transcript_buffer
                        ),
                    }
                ],
                temperature=0.1,
                max_tokens=150,
                response_format={"type": "json_object"},
            )

            raw = response.choices[0].message.content
            parsed = json.loads(raw)

            return QuestionDetectionResult(
                is_question=parsed.get("is_question", False),
                confidence=float(parsed.get("confidence", 0.0)),
                cleaned_question=parsed.get("cleaned_question"),
                question_type=parsed.get("question_type"),
            )

        except json.JSONDecodeError as e:
            log.warning("Question detector JSON parse error", error=str(e))
            return QuestionDetectionResult(
                is_question=False,
                confidence=0.0,
                cleaned_question=None,
                question_type=None,
            )
        except Exception as e:
            log.error("Question detector error", error=str(e))
            raise
Mission 0.5 — LLM Router
backend/app/services/llm_router.py
Python

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass

import structlog
from groq import AsyncGroq
from openai import AsyncOpenAI

from app.config import get_settings

log = structlog.get_logger()
settings = get_settings()

ANSWER_SYSTEM_PROMPT = """You are helping {candidate_name} answer an interview question in real-time.

RULES:
- Respond in FIRST PERSON as if the candidate is speaking
- Be concise: 100-150 words for behavioral/technical questions
- Use STAR format (Situation, Task, Action, Result) for behavioral questions
- Ground EVERY answer in the candidate's actual background below
- Do NOT fabricate experience not present in the context
- Do NOT start with "I would say" or similar meta-phrases — just answer directly

## Candidate Background (from their resume):
{rag_chunks}

## Job Description Highlights:
{jd_summary}

## Recent Conversation Context:
{conversation_history}
"""

USER_PROMPT_TEMPLATE = """Interview Question: {question}

Provide a strong, personalized answer based on the candidate's background above."""


@dataclass
class LLMContext:
    candidate_name: str
    rag_chunks: str
    jd_summary: str
    conversation_history: str
    question: str


class LLMProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    async def generate_stream(
        self,
        context: LLMContext,
    ) -> AsyncGenerator[str, None]:
        """Yield tokens as they are generated."""
        ...


class GroqProvider(LLMProvider):
    """
    Groq Llama-3.3-70B — fastest inference for real-time UX.
    Target TTFT: < 400ms.
    """

    def __init__(self) -> None:
        self.client = AsyncGroq(api_key=settings.groq_api_key)

    async def generate_stream(
        self,
        context: LLMContext,
    ) -> AsyncGenerator[str, None]:
        system_prompt = ANSWER_SYSTEM_PROMPT.format(
            candidate_name=context.candidate_name,
            rag_chunks=context.rag_chunks,
            jd_summary=context.jd_summary,
            conversation_history=context.conversation_history,
        )

        stream = await self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": USER_PROMPT_TEMPLATE.format(
                    question=context.question
                )},
            ],
            temperature=0.7,
            max_tokens=300,
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


class OpenAIProvider(LLMProvider):
    """
    OpenAI GPT-4.1 — higher quality, used for mock mode or when user opts in.
    """

    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def generate_stream(
        self,
        context: LLMContext,
    ) -> AsyncGenerator[str, None]:
        system_prompt = ANSWER_SYSTEM_PROMPT.format(
            candidate_name=context.candidate_name,
            rag_chunks=context.rag_chunks,
            jd_summary=context.jd_summary,
            conversation_history=context.conversation_history,
        )

        stream = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": USER_PROMPT_TEMPLATE.format(
                    question=context.question
                )},
            ],
            temperature=0.7,
            max_tokens=300,
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


def get_llm_provider(provider: str | None = None) -> LLMProvider:
    """Factory function — returns the configured LLM provider."""
    target = provider or settings.llm_provider
    if target == "groq":
        return GroqProvider()
    elif target == "openai":
        return OpenAIProvider()
    else:
        raise ValueError(f"Unknown LLM provider: {target}")
Mission 0.6 — Session Manager (Redis)
backend/app/services/session_manager.py
Python

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
    Handles transcript buffer, Q&A history, and session metadata.
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
            "created_at": time.time(),
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
Mission 0.7 — WebSocket Pipeline (Integration)
backend/app/routers/websocket.py
Python

import asyncio
import json
import time
import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.config import get_settings
from app.services.stt.deepgram import DeepgramProvider
from app.services.vad import SileroVAD, VADState
from app.services.question_detector import QuestionDetector
from app.services.llm_router import get_llm_provider, LLMContext
from app.services.session_manager import SessionManager

log = structlog.get_logger()
settings = get_settings()
router = APIRouter()

# Singletons loaded once at startup
_vad = SileroVAD(silence_threshold_ms=settings.vad_silence_threshold_ms)
_question_detector = QuestionDetector()


async def _send_json(ws: WebSocket, data: dict) -> None:
    """Safe JSON send — ignores errors on closed connections."""
    try:
        if ws.client_state == WebSocketState.CONNECTED:
            await ws.send_json(data)
    except Exception:
        pass


@router.websocket("/ws/session/{session_id}")
async def websocket_session(ws: WebSocket, session_id: str) -> None:
    await ws.accept()
    log.info("WebSocket connected", session_id=session_id)

    redis = ws.app.state.redis
    session_mgr = SessionManager(redis)
    stt_provider = DeepgramProvider()
    llm_provider = get_llm_provider()

    vad_state = VADState()
    audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=100)

    # ── Audio → STT generator bridge ─────────────────────────────────

    async def audio_generator():
        while True:
            chunk = await audio_queue.get()
            if chunk is None:
                break
            yield chunk

    # ── Process STT transcript events ─────────────────────────────────

    async def process_transcripts() -> None:
        nonlocal vad_state

        async for event in stt_provider.stream_audio(audio_generator()):
            # Send transcript to client
            msg_type = (
                "transcript_final" if event.is_final else "transcript_partial"
            )
            await _send_json(ws, {
                "type": msg_type,
                "speaker": event.speaker or "unknown",
                "text": event.text,
                "is_question": False,
            })

            # Store final transcripts in Redis
            if event.is_final and event.text.strip():
                await session_mgr.append_transcript(
                    session_id=session_id,
                    speaker=event.speaker or "0",
                    text=event.text,
                    timestamp_ms=event.timestamp_ms,
                )

    # ── Process audio chunks through VAD ──────────────────────────────

    async def process_audio_chunk(pcm_chunk: bytes) -> None:
        nonlocal vad_state

        vad_state, end_of_utterance = _vad.process_chunk(pcm_chunk, vad_state)

        if not end_of_utterance:
            return

        # End of utterance detected — classify as question
        transcript_buffer = await session_mgr.get_recent_transcript(
            session_id, seconds=15
        )
        if not transcript_buffer:
            return

        detection = await _question_detector.classify(transcript_buffer)

        log.info(
            "Question detection",
            is_question=detection.is_question,
            confidence=detection.confidence,
        )

        if (
            not detection.is_question
            or detection.confidence < settings.question_confidence_threshold
        ):
            return

        # Signal question detected to client
        await _send_json(ws, {
            "type": "transcript_final",
            "speaker": "0",
            "text": detection.cleaned_question or "",
            "is_question": True,
        })

        # Generate answer
        await generate_answer(detection.cleaned_question or "")

    # ── Generate and stream answer ─────────────────────────────────────

    async def generate_answer(question: str) -> None:
        start_ms = time.time() * 1000
        qa_history = await session_mgr.get_qa_history(session_id)
        meta = await session_mgr.get_meta(session_id)
        candidate_name = meta.get("candidate_name", "the candidate")

        context = LLMContext(
            candidate_name=candidate_name,
            rag_chunks="[Resume context will be added in Phase 1]",
            jd_summary="[JD context will be added in Phase 1]",
            conversation_history=qa_history,
            question=question,
        )

        full_answer = []
        first_token = True

        async for token in llm_provider.generate_stream(context):
            full_answer.append(token)
            await _send_json(ws, {"type": "answer_token", "token": token})

            if first_token:
                latency = int(time.time() * 1000 - start_ms)
                log.info("First token latency", latency_ms=latency)
                first_token = False

        answer_text = "".join(full_answer)
        total_latency = int(time.time() * 1000 - start_ms)

        await _send_json(ws, {
            "type": "answer_complete",
            "full_text": answer_text,
            "latency_ms": total_latency,
        })

        # Store Q&A in Redis
        await session_mgr.append_qa(session_id, question, answer_text)

        log.info(
            "Answer generated",
            session_id=session_id,
            latency_ms=total_latency,
        )

    # ── Main WebSocket Loop ────────────────────────────────────────────

    # Start STT processing in background
    stt_task = asyncio.create_task(process_transcripts())

    try:
        # Create session in Redis if not exists
        await session_mgr.create_session(
            session_id=session_id,
            user_id="test_user",  # Replace with auth in Phase 2
            candidate_name="Candidate",
        )

        while True:
            message = await ws.receive()

            if message["type"] == "websocket.disconnect":
                break

            if message["type"] == "websocket.receive":
                if "bytes" in message and message["bytes"]:
                    # Binary PCM audio chunk
                    pcm_chunk = message["bytes"]
                    await audio_queue.put(pcm_chunk)
                    await process_audio_chunk(pcm_chunk)

                elif "text" in message and message["text"]:
                    # Control messages
                    try:
                        control = json.loads(message["text"])
                        if control.get("type") == "control":
                            action = control.get("action")
                            if action == "end_session":
                                await session_mgr.end_session(session_id)
                    except json.JSONDecodeError:
                        pass

    except WebSocketDisconnect:
        log.info("WebSocket disconnected", session_id=session_id)
    except Exception as e:
        log.error("WebSocket error", session_id=session_id, error=str(e))
        await _send_json(ws, {"type": "error", "message": str(e)})
    finally:
        await audio_queue.put(None)
        stt_task.cancel()
        await stt_provider.close()
        log.info("WebSocket cleanup complete", session_id=session_id)
Mission 0.8 — Test Client
frontend/test.html
HTML

<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>InterviewCopilot — Pipeline Test Harness</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: 'Courier New', monospace;
      background: #0a0a0f;
      color: #e0e0e0;
      height: 100vh;
      display: grid;
      grid-template-rows: auto 1fr;
    }
    header {
      background: #12121a;
      padding: 16px 24px;
      border-bottom: 1px solid #2a2a3a;
      display: flex;
      align-items: center;
      gap: 16px;
    }
    header h1 { font-size: 18px; color: #7c6ff7; }
    .status-dot {
      width: 10px; height: 10px;
      border-radius: 50%;
      background: #444;
      transition: background 0.3s;
    }
    .status-dot.connected { background: #22c55e; }
    .status-dot.recording { background: #ef4444; animation: pulse 1s infinite; }
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.4; }
    }
    .latency-badge {
      margin-left: auto;
      font-size: 12px;
      color: #888;
    }
    .latency-badge span { color: #22c55e; font-weight: bold; }
    main {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0;
      overflow: hidden;
    }
    .panel {
      display: flex;
      flex-direction: column;
      overflow: hidden;
      border-right: 1px solid #2a2a3a;
    }
    .panel-header {
      padding: 12px 16px;
      background: #12121a;
      border-bottom: 1px solid #2a2a3a;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 2px;
      color: #666;
    }
    .panel-body {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .transcript-entry {
      font-size: 13px;
      line-height: 1.6;
      padding: 8px 12px;
      border-radius: 6px;
      border-left: 3px solid transparent;
    }
    .transcript-entry.interviewer {
      border-left-color: #7c6ff7;
      background: rgba(124, 111, 247, 0.08);
    }
    .transcript-entry.candidate {
      border-left-color: #22c55e;
      background: rgba(34, 197, 94, 0.08);
    }
    .transcript-entry.question {
      border-left-color: #f59e0b;
      background: rgba(245, 158, 11, 0.1);
    }
    .transcript-entry .label {
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 1px;
      margin-bottom: 4px;
      opacity: 0.6;
    }
    .answer-block {
      background: #12121a;
      border: 1px solid #2a2a3a;
      border-radius: 8px;
      padding: 16px;
      font-size: 14px;
      line-height: 1.8;
      color: #d4d4d4;
    }
    .answer-block .answer-header {
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: #7c6ff7;
      margin-bottom: 8px;
    }
    .answer-block .answer-text { color: #e0e0e0; }
    .answer-block .latency-info {
      margin-top: 8px;
      font-size: 11px;
      color: #555;
    }
    .controls {
      padding: 16px;
      background: #12121a;
      border-top: 1px solid #2a2a3a;
      display: flex;
      gap: 12px;
      align-items: center;
    }
    button {
      padding: 8px 20px;
      border-radius: 6px;
      border: none;
      font-size: 13px;
      cursor: pointer;
      font-family: inherit;
      transition: all 0.2s;
    }
    .btn-primary {
      background: #7c6ff7;
      color: white;
    }
    .btn-primary:hover { background: #6b5ee6; }
    .btn-primary:disabled { opacity: 0.4; cursor: not-allowed; }
    .btn-danger {
      background: #ef4444;
      color: white;
    }
    .btn-danger:hover { background: #dc2626; }
    .session-id-display {
      font-size: 11px;
      color: #555;
      margin-left: auto;
    }
  </style>
</head>
<body>
  <header>
    <div class="status-dot" id="statusDot"></div>
    <h1>InterviewCopilot — Pipeline Test</h1>
    <div class="latency-badge">
      Last latency: <span id="latencyDisplay">—</span>
    </div>
  </header>

  <main>
    <div class="panel">
      <div class="panel-header">Live Transcript</div>
      <div class="panel-body" id="transcriptPanel"></div>
      <div class="controls">
        <button class="btn-primary" id="startBtn">Start Recording</button>
        <button class="btn-danger" id="stopBtn" disabled>Stop</button>
        <span class="session-id-display" id="sessionIdDisplay"></span>
      </div>
    </div>

    <div class="panel">
      <div class="panel-header">AI Answers</div>
      <div class="panel-body" id="answersPanel"></div>
    </div>
  </main>

  <script>
    const WS_URL = 'ws://localhost:8000';
    const statusDot = document.getElementById('statusDot');
    const transcriptPanel = document.getElementById('transcriptPanel');
    const answersPanel = document.getElementById('answersPanel');
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const latencyDisplay = document.getElementById('latencyDisplay');
    const sessionIdDisplay = document.getElementById('sessionIdDisplay');

    let ws = null;
    let audioContext = null;
    let processor = null;
    let stream = null;
    let currentAnswerBlock = null;
    let questionStartTime = null;

    function generateSessionId() {
      return 'test-' + Math.random().toString(36).substr(2, 9);
    }

    function addTranscriptEntry(speaker, text, isQuestion) {
      const entry = document.createElement('div');
      const speakerClass = isQuestion ? 'question' :
        (speaker === '0' ? 'interviewer' : 'candidate');
      entry.className = `transcript-entry ${speakerClass}`;

      const speakerLabel = isQuestion ? '🎯 QUESTION DETECTED' :
        (speaker === '0' ? '🎤 Interviewer' : '🗣️ Candidate');

      entry.innerHTML = `
        <div class="label">${speakerLabel}</div>
        <div>${text}</div>
      `;
      transcriptPanel.appendChild(entry);
      transcriptPanel.scrollTop = transcriptPanel.scrollHeight;
    }

    function startNewAnswer() {
      questionStartTime = Date.now();
      currentAnswerBlock = document.createElement('div');
      currentAnswerBlock.className = 'answer-block';
      currentAnswerBlock.innerHTML = `
        <div class="answer-header">🤖 Generating answer...</div>
        <div class="answer-text" id="currentAnswerText"></div>
        <div class="latency-info"></div>
      `;
      answersPanel.appendChild(currentAnswerBlock);
      answersPanel.scrollTop = answersPanel.scrollHeight;
    }

    function appendAnswerToken(token) {
      if (!currentAnswerBlock) startNewAnswer();
      const textEl = currentAnswerBlock.querySelector('#currentAnswerText');
      if (textEl) {
        textEl.textContent += token;
        answersPanel.scrollTop = answersPanel.scrollHeight;
      }
    }

    function finalizeAnswer(latencyMs) {
      if (!currentAnswerBlock) return;
      const header = currentAnswerBlock.querySelector('.answer-header');
      const latencyInfo = currentAnswerBlock.querySelector('.latency-info');
      if (header) header.textContent = '✅ Answer ready';
      if (latencyInfo) latencyInfo.textContent = `Generated in ${latencyMs}ms`;
      latencyDisplay.textContent = `${latencyMs}ms`;
      currentAnswerBlock = null;
    }

    async function connectWebSocket(sessionId) {
      ws = new WebSocket(`${WS_URL}/ws/session/${sessionId}`);

      ws.onopen = () => {
        statusDot.className = 'status-dot connected';
        console.log('WebSocket connected');
      };

      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);

        switch (msg.type) {
          case 'transcript_partial':
            // Could show interim results here
            break;

          case 'transcript_final':
            addTranscriptEntry(msg.speaker, msg.text, msg.is_question);
            if (msg.is_question) startNewAnswer();
            break;

          case 'answer_token':
            appendAnswerToken(msg.token);
            break;

          case 'answer_complete':
            finalizeAnswer(msg.latency_ms);
            break;

          case 'error':
            console.error('Server error:', msg.message);
            break;
        }
      };

      ws.onclose = () => {
        statusDot.className = 'status-dot';
        console.log('WebSocket disconnected');
      };

      ws.onerror = (err) => {
        console.error('WebSocket error:', err);
      };
    }

    async function startRecording() {
      const sessionId = generateSessionId();
      sessionIdDisplay.textContent = `Session: ${sessionId}`;

      await connectWebSocket(sessionId);

      // Wait for connection
      await new Promise(resolve => {
        const check = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            clearInterval(check);
            resolve();
          }
        }, 100);
      });

      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        }
      });

      audioContext = new AudioContext({ sampleRate: 16000 });
      const source = audioContext.createMediaStreamSource(stream);

      // Use ScriptProcessor for broad compatibility
      // (AudioWorklet is better for production)
      processor = audioContext.createScriptProcessor(4096, 1, 1);

      processor.onaudioprocess = (e) => {
        if (ws.readyState !== WebSocket.OPEN) return;

        const float32 = e.inputBuffer.getChannelData(0);
        // Convert Float32 → Int16 PCM
        const int16 = new Int16Array(float32.length);
        for (let i = 0; i < float32.length; i++) {
          const clamped = Math.max(-1, Math.min(1, float32[i]));
          int16[i] = clamped < 0 ? clamped * 32768 : clamped * 32767;
        }
        ws.send(int16.buffer);
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      statusDot.className = 'status-dot recording';
      startBtn.disabled = true;
      stopBtn.disabled = false;

      console.log('Recording started, session:', sessionId);
    }

    function stopRecording() {
      if (processor) { processor.disconnect(); processor = null; }
      if (audioContext) { audioContext.close(); audioContext = null; }
      if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null; }
      if (ws) {
        ws.send(JSON.stringify({ type: 'control', action: 'end_session' }));
        ws.close();
        ws = null;
      }
      statusDot.className = 'status-dot';
      startBtn.disabled = false;
      stopBtn.disabled = true;
    }

    startBtn.addEventListener('click', startRecording);
    stopBtn.addEventListener('click', stopRecording);
  </script>
</body>
</html>
Phase 1 — RAG + Document Pipeline
Mission 1.1 — Database Models
backend/app/models/user.py
Python

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    plan: Mapped[str] = mapped_column(String, default="free")
    credits: Mapped[int] = mapped_column(default=5)  # 5 free sessions
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
backend/app/models/session.py
Python

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
backend/app/models/document_chunk.py
Python

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.database import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String, ForeignKey("sessions.id"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(String)  # resume | jd
    section: Mapped[str | None] = mapped_column(String, nullable=True)
    chunk_text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
Mission 1.2 — Document Parser
backend/app/services/document_parser.py
Python

import re
import structlog
import pdfplumber
from docx import Document
from dataclasses import dataclass
from io import BytesIO

log = structlog.get_logger()

SECTION_HEADERS = [
    "experience", "work experience", "employment", "professional experience",
    "education", "projects", "skills", "technical skills", "summary",
    "objective", "certifications", "achievements", "publications",
]

MAX_CHUNK_SIZE = 500  # characters
CHUNK_OVERLAP = 50


@dataclass
class DocumentChunk:
    text: str
    section: str
    source_type: str  # resume | jd


class DocumentParser:
    """Parse PDF/DOCX resumes and JD text into structured chunks."""

    def parse_resume(self, file_bytes: bytes, file_type: str) -> str:
        """Extract raw text from resume file."""
        if file_type == "pdf":
            return self._parse_pdf(file_bytes)
        elif file_type in ("docx", "doc"):
            return self._parse_docx(file_bytes)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    def _parse_pdf(self, file_bytes: bytes) -> str:
        text_parts = []
        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
        return "\n".join(text_parts)

    def _parse_docx(self, file_bytes: bytes) -> str:
        doc = Document(BytesIO(file_bytes))
        return "\n".join(
            para.text for para in doc.paragraphs if para.text.strip()
        )

    def chunk_resume(self, text: str) -> list[DocumentChunk]:
        """Split resume text into semantic section-based chunks."""
        sections = self._split_by_sections(text)
        chunks = []

        for section_name, section_text in sections.items():
            # Further split large sections
            sub_chunks = self._split_text(section_text, MAX_CHUNK_SIZE)
            for chunk_text in sub_chunks:
                if chunk_text.strip():
                    chunks.append(DocumentChunk(
                        text=chunk_text.strip(),
                        section=section_name,
                        source_type="resume",
                    ))

        log.info("Resume chunked", num_chunks=len(chunks))
        return chunks

    def chunk_jd(self, text: str) -> list[DocumentChunk]:
        """Split JD text into chunks."""
        chunks = self._split_text(text, MAX_CHUNK_SIZE)
        return [
            DocumentChunk(
                text=chunk.strip(),
                section="job_description",
                source_type="jd",
            )
            for chunk in chunks if chunk.strip()
        ]

    def _split_by_sections(self, text: str) -> dict[str, str]:
        """Detect resume sections by header keywords."""
        lines = text.split("\n")
        sections: dict[str, list[str]] = {"general": []}
        current_section = "general"

        for line in lines:
            line_lower = line.lower().strip()
            is_header = any(
                header in line_lower
                for header in SECTION_HEADERS
            ) and len(line.strip()) < 50

            if is_header:
                current_section = line.strip().lower()
                sections[current_section] = []
            else:
                sections.setdefault(current_section, []).append(line)

        return {k: "\n".join(v) for k, v in sections.items() if v}

    def _split_text(self, text: str, max_size: int) -> list[str]:
        """Split text into overlapping chunks by sentence boundaries."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = []
        current_size = 0

        for sentence in sentences:
            if current_size + len(sentence) > max_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                # Keep last sentence for overlap
                current_chunk = current_chunk[-1:] if CHUNK_OVERLAP else []
                current_size = sum(len(s) for s in current_chunk)

            current_chunk.append(sentence)
            current_size += len(sentence)

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks
Mission 1.3 — RAG Service
backend/app/services/rag.py
Python

import structlog
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.config import get_settings
from app.services.document_parser import DocumentParser, DocumentChunk
from app.models.document_chunk import DocumentChunk as DocumentChunkModel

log = structlog.get_logger()
settings = get_settings()


class RAGService:
    """
    Resume/JD embedding ingestion and retrieval.
    Uses pgvector for similarity search.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.parser = DocumentParser()
        self.openai = AsyncOpenAI(api_key=settings.openai_api_key)

    async def _embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts using OpenAI embeddings."""
        response = await self.openai.embeddings.create(
            model=settings.embedding_model,
            input=texts,
        )
        return [item.embedding for item in response.data]

    async def ingest_resume(
        self,
        session_id: str,
        file_bytes: bytes,
        file_type: str,
    ) -> int:
        """Parse resume, embed chunks, store in pgvector."""
        raw_text = self.parser.parse_resume(file_bytes, file_type)
        chunks = self.parser.chunk_resume(raw_text)
        return await self._store_chunks(session_id, chunks)

    async def ingest_jd(self, session_id: str, jd_text: str) -> int:
        """Embed JD text, store in pgvector."""
        chunks = self.parser.chunk_jd(jd_text)
        return await self._store_chunks(session_id, chunks)

    async def _store_chunks(
        self,
        session_id: str,
        chunks: list[DocumentChunk],
    ) -> int:
        """Embed and store document chunks."""
        if not chunks:
            return 0

        texts = [c.text for c in chunks]
        embeddings = await self._embed(texts)

        db_chunks = [
            DocumentChunkModel(
                session_id=session_id,
                source_type=chunks[i].source_type,
                section=chunks[i].section,
                chunk_text=chunks[i].text,
                embedding=embeddings[i],
            )
            for i in range(len(chunks))
        ]

        self.db.add_all(db_chunks)
        await self.db.flush()

        log.info(
            "Chunks stored",
            session_id=session_id,
            count=len(db_chunks),
        )
        return len(db_chunks)

    async def retrieve(
        self,
        session_id: str,
        question: str,
        top_k: int = 4,
    ) -> str:
        """
        Find most relevant resume/JD chunks for a given question.
        Returns formatted context string for LLM prompt.
        """
        question_embedding = (await self._embed([question]))[0]

        # pgvector cosine similarity search
        result = await self.db.execute(
            text("""
                SELECT chunk_text, section, source_type,
                       1 - (embedding <=> :embedding::vector) as similarity
                FROM document_chunks
                WHERE session_id = :session_id
                ORDER BY embedding <=> :embedding::vector
                LIMIT :top_k
            """),
            {
                "embedding": str(question_embedding),
                "session_id": session_id,
                "top_k": top_k,
            },
        )

        rows = result.fetchall()
        if not rows:
            return "No resume context available."

        context_parts = []
        for row in rows:
            section_label = f"[{row.source_type.upper()} — {row.section}]"
            context_parts.append(f"{section_label}\n{row.chunk_text}")

        return "\n\n".join(context_parts)
Phase 2 — Web Application
Mission 2.1 — Auth System
backend/app/routers/auth.py
Python

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr

from app.config import get_settings
from app.database import get_db
from app.models.user import User

router = APIRouter()
settings = get_settings()
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Schemas ───────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr
    name: str
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    name: str


# ── JWT Helpers ───────────────────────────────────────────────────────

def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    return jwt.encode(
        {"sub": user_id, "exp": expire, "type": "access"},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.jwt_refresh_token_expire_days
    )
    return jwt.encode(
        {"sub": user_id, "exp": expire, "type": "refresh"},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


# ── Endpoints ─────────────────────────────────────────────────────────

@router.post("/signup", response_model=TokenResponse)
async def signup(
    body: SignupRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    # Check if email exists
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=body.email,
        name=body.name,
        hashed_password=pwd_context.hash(body.password),
        plan="free",
        credits=5,
    )
    db.add(user)
    await db.flush()

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user_id=user.id,
        name=user.name or "",
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not pwd_context.verify(body.password, user.hashed_password):
        raise HTTPException(
            status_code=401, detail="Invalid email or password"
        )

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user_id=user.id,
        name=user.name or "",
    )
Mission 2.2 — React Frontend
frontend/package.json
JSON

{
  "name": "interviewcopilot-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "test": "vitest"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.2",
    "zustand": "^5.0.0",
    "lucide-react": "^0.441.0",
    "clsx": "^2.1.1"
  },
  "devDependencies": {
    "@types/react": "^18.3.5",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.45",
    "tailwindcss": "^3.4.12",
    "typescript": "^5.5.3",
    "vite": "^5.4.6",
    "vitest": "^2.1.1"
  }
}
frontend/src/hooks/useWebSocket.ts
TypeScript

import { useEffect, useRef, useCallback, useState } from 'react'

export type WSMessage =
  | { type: 'transcript_partial'; speaker: string; text: string }
  | { type: 'transcript_final'; speaker: string; text: string; is_question: boolean }
  | { type: 'answer_token'; token: string }
  | { type: 'answer_complete'; full_text: string; latency_ms: number }
  | { type: 'error'; message: string }

type MessageHandler = (msg: WSMessage) => void

export function useWebSocket(sessionId: string | null) {
  const ws = useRef<WebSocket | null>(null)
  const handlers = useRef<Set<MessageHandler>>(new Set())
  const [connected, setConnected] = useState(false)

  const connect = useCallback(() => {
    if (!sessionId || ws.current?.readyState === WebSocket.OPEN) return

    const url = `ws://localhost:8000/ws/session/${sessionId}`
    ws.current = new WebSocket(url)

    ws.current.onopen = () => {
      setConnected(true)
      console.log('[WS] Connected:', sessionId)
    }

    ws.current.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data) as WSMessage
        handlers.current.forEach(h => h(msg))
      } catch (e) {
        console.error('[WS] Parse error:', e)
      }
    }

    ws.current.onclose = () => {
      setConnected(false)
      console.log('[WS] Disconnected')
    }

    ws.current.onerror = (err) => {
      console.error('[WS] Error:', err)
    }
  }, [sessionId])

  const disconnect = useCallback(() => {
    ws.current?.close()
    ws.current = null
    setConnected(false)
  }, [])

  const sendBinary = useCallback((data: ArrayBuffer) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(data)
    }
  }, [])

  const sendJSON = useCallback((data: object) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data))
    }
  }, [])

  const onMessage = useCallback((handler: MessageHandler) => {
    handlers.current.add(handler)
    return () => handlers.current.delete(handler)
  }, [])

  useEffect(() => {
    if (sessionId) connect()
    return () => disconnect()
  }, [sessionId, connect, disconnect])

  return { connected, connect, disconnect, sendBinary, sendJSON, onMessage }
}
frontend/src/hooks/useAudioCapture.ts
TypeScript

import { useRef, useCallback, useState } from 'react'

const SAMPLE_RATE = 16000

export function useAudioCapture(onPCMChunk: (chunk: ArrayBuffer) => void) {
  const audioContext = useRef<AudioContext | null>(null)
  const processor = useRef<ScriptProcessorNode | null>(null)
  const stream = useRef<MediaStream | null>(null)
  const [isRecording, setIsRecording] = useState(false)

  const start = useCallback(async () => {
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: SAMPLE_RATE,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        }
      })

      audioContext.current = new AudioContext({ sampleRate: SAMPLE_RATE })
      const source = audioContext.current.createMediaStreamSource(stream.current)

      // ScriptProcessor for simplicity (AudioWorklet for production)
      processor.current = audioContext.current.createScriptProcessor(4096, 1, 1)

      processor.current.onaudioprocess = (e: AudioProcessingEvent) => {
        const float32 = e.inputBuffer.getChannelData(0)
        const int16 = new Int16Array(float32.length)

        for (let i = 0; i < float32.length; i++) {
          const clamped = Math.max(-1, Math.min(1, float32[i]))
          int16[i] = clamped < 0 ? clamped * 32768 : clamped * 32767
        }

        onPCMChunk(int16.buffer)
      }

      source.connect(processor.current)
      processor.current.connect(audioContext.current.destination)
      setIsRecording(true)

    } catch (err) {
      console.error('[Audio] Failed to start capture:', err)
      throw err
    }
  }, [onPCMChunk])

  const stop = useCallback(() => {
    processor.current?.disconnect()
    processor.current = null
    audioContext.current?.close()
    audioContext.current = null
    stream.current?.getTracks().forEach(t => t.stop())
    stream.current = null
    setIsRecording(false)
  }, [])

  return { isRecording, start, stop }
}
frontend/src/pages/InterviewPage.tsx
TypeScript

import { useState, useEffect, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { Mic, MicOff, Clock, ChevronRight } from 'lucide-react'
import { useWebSocket, WSMessage } from '../hooks/useWebSocket'
import { useAudioCapture } from '../hooks/useAudioCapture'
import clsx from 'clsx'

interface TranscriptEntry {
  id: string
  speaker: string
  text: string
  isQuestion: boolean
  timestamp: number
}

interface AnswerEntry {
  id: string
  question: string
  text: string
  latencyMs: number | null
  isStreaming: boolean
}

export default function InterviewPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([])
  const [answers, setAnswers] = useState<AnswerEntry[]>([])
  const [currentStreamingId, setCurrentStreamingId] = useState<string | null>(null)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [lastLatency, setLastLatency] = useState<number | null>(null)

  const { connected, sendBinary, onMessage } = useWebSocket(sessionId ?? null)

  const handlePCMChunk = useCallback((chunk: ArrayBuffer) => {
    sendBinary(chunk)
  }, [sendBinary])

  const { isRecording, start, stop } = useAudioCapture(handlePCMChunk)

  // Handle incoming WebSocket messages
  useEffect(() => {
    const unsubscribe = onMessage((msg: WSMessage) => {
      switch (msg.type) {
        case 'transcript_final': {
          const entry: TranscriptEntry = {
            id: crypto.randomUUID(),
            speaker: msg.speaker,
            text: msg.text,
            isQuestion: msg.is_question,
            timestamp: Date.now(),
          }
          setTranscript(prev => [...prev, entry])

          if (msg.is_question) {
            const answerId = crypto.randomUUID()
            setCurrentStreamingId(answerId)
            setAnswers(prev => [...prev, {
              id: answerId,
              question: msg.text,
              text: '',
              latencyMs: null,
              isStreaming: true,
            }])
          }
          break
        }

        case 'answer_token': {
          if (!currentStreamingId) break
          setAnswers(prev => prev.map(a =>
            a.id === currentStreamingId
              ? { ...a, text: a.text + msg.token }
              : a
          ))
          break
        }

        case 'answer_complete': {
          setAnswers(prev => prev.map(a =>
            a.id === currentStreamingId
              ? { ...a, latencyMs: msg.latency_ms, isStreaming: false }
              : a
          ))
          setLastLatency(msg.latency_ms)
          setCurrentStreamingId(null)
          break
        }
      }
    })
    return unsubscribe
  }, [onMessage, currentStreamingId])

  // Timer
  useEffect(() => {
    if (!isRecording) return
    const interval = setInterval(() => {
      setElapsedSeconds(s => s + 1)
    }, 1000)
    return () => clearInterval(interval)
  }, [isRecording])

  const formatTime = (s: number) => {
    const m = Math.floor(s / 60)
    const sec = s % 60
    return `${m}:${sec.toString().padStart(2, '0')}`
  }

  return (
    <div className="h-screen bg-gray-950 flex flex-col">
      {/* Header */}
      <header className="bg-gray-900 border-b border-gray-800 px-6 py-4 flex items-center gap-4">
        <div className={clsx(
          'w-2.5 h-2.5 rounded-full transition-all',
          connected ? 'bg-green-500' : 'bg-gray-600'
        )} />
        <h1 className="text-white font-semibold">InterviewCopilot</h1>

        <div className="flex items-center gap-2 ml-4 text-gray-400 text-sm">
          <Clock size={14} />
          <span>{formatTime(elapsedSeconds)}</span>
        </div>

        {lastLatency && (
          <span className="text-xs text-gray-500">
            Last response: <span className="text-green-400">{lastLatency}ms</span>
          </span>
        )}

        <div className="ml-auto flex gap-3">
          <button
            onClick={isRecording ? stop : start}
            disabled={!connected}
            className={clsx(
              'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all',
              isRecording
                ? 'bg-red-600 hover:bg-red-700 text-white'
                : 'bg-indigo-600 hover:bg-indigo-700 text-white disabled:opacity-40'
            )}
          >
            {isRecording ? <MicOff size={16} /> : <Mic size={16} />}
            {isRecording ? 'Stop' : 'Start Recording'}
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 grid grid-cols-2 overflow-hidden">
        {/* Left: Transcript */}
        <div className="flex flex-col border-r border-gray-800 overflow-hidden">
          <div className="px-4 py-3 bg-gray-900 border-b border-gray-800">
            <p className="text-xs text-gray-500 uppercase tracking-widest">
              Live Transcript
            </p>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {transcript.map(entry => (
              <div
                key={entry.id}
                className={clsx(
                  'rounded-lg px-4 py-3 border-l-2 text-sm leading-relaxed',
                  entry.isQuestion
                    ? 'border-amber-400 bg-amber-400/5 text-amber-100'
                    : entry.speaker === '0'
                    ? 'border-indigo-500 bg-indigo-500/5 text-gray-300'
                    : 'border-green-500 bg-green-500/5 text-gray-300'
                )}
              >
                <div className="text-xs opacity-50 mb-1 uppercase tracking-wider">
                  {entry.isQuestion
                    ? '🎯 Question detected'
                    : entry.speaker === '0' ? 'Interviewer' : 'You'}
                </div>
                {entry.text}
              </div>
            ))}
          </div>
        </div>

        {/* Right: AI Answers */}
        <div className="flex flex-col overflow-hidden">
          <div className="px-4 py-3 bg-gray-900 border-b border-gray-800">
            <p className="text-xs text-gray-500 uppercase tracking-widest">
              AI Suggested Answer
            </p>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {answers.map(answer => (
              <div
                key={answer.id}
                className="bg-gray-900 border border-gray-800 rounded-xl p-5"
              >
                <div className="flex items-start gap-2 mb-3">
                  <ChevronRight size={14} className="text-indigo-400 mt-0.5 shrink-0" />
                  <p className="text-xs text-indigo-300">{answer.question}</p>
                </div>
                <p className="text-gray-200 text-sm leading-relaxed">
                  {answer.text}
                  {answer.isStreaming && (
                    <span className="inline-block w-1 h-4 bg-indigo-400 ml-0.5 animate-pulse" />
                  )}
                </p>
                {answer.latencyMs && (
                  <p className="text-xs text-gray-600 mt-3">
                    Generated in {answer.latencyMs}ms
                  </p>
                )}
              </div>
            ))}

            {answers.length === 0 && (
              <div className="flex items-center justify-center h-full">
                <p className="text-gray-600 text-sm text-center">
                  Start recording and speak a question<br />
                  to see AI-suggested answers here.
                </p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
Tests
backend/tests/benchmark_latency.py
Python

"""
Latency benchmark for the full pipeline.
Run: python -m tests.benchmark_latency
Must pass: < 2000ms end-to-end
"""
import asyncio
import time
import wave
import numpy as np
import structlog
from app.services.question_detector import QuestionDetector
from app.services.llm_router import get_llm_provider, LLMContext

log = structlog.get_logger()

TEST_QUESTIONS = [
    "Tell me about a time you had to solve a difficult technical problem.",
    "How do you handle disagreements with your team?",
    "What's your approach to system design for high-traffic applications?",
]

async def benchmark_question_detector():
    detector = QuestionDetector()
    latencies = []

    for question in TEST_QUESTIONS:
        start = time.perf_counter()
        result = await detector.classify(f"Interviewer: {question}")
        latency = (time.perf_counter() - start) * 1000
        latencies.append(latency)
        log.info("Classifier", question=question[:50], latency_ms=round(latency))
        assert result.is_question, f"Failed to classify: {question}"

    avg = sum(latencies) / len(latencies)
    log.info("Question classifier avg latency", avg_ms=round(avg))
    assert avg < 300, f"Classifier too slow: {avg:.0f}ms (target: <300ms)"

async def benchmark_llm_ttft():
    """Time-to-first-token benchmark."""
    provider = get_llm_provider()
    latencies = []

    for question in TEST_QUESTIONS:
        context = LLMContext(
            candidate_name="John Doe",
            rag_chunks="Senior engineer with 5 years at Google. Led backend systems.",
            jd_summary="Backend engineer role requiring Python, distributed systems.",
            conversation_history="No previous exchanges.",
            question=question,
        )

        start = time.perf_counter()
        first_token_received = False

        async for token in provider.generate_stream(context):
            if not first_token_received:
                ttft = (time.perf_counter() - start) * 1000
                latencies.append(ttft)
                log.info("TTFT", latency_ms=round(ttft))
                first_token_received = True
                break  # Only measure first token

    avg = sum(latencies) / len(latencies)
    log.info("LLM TTFT avg", avg_ms=round(avg))
    assert avg < 600, f"TTFT too slow: {avg:.0f}ms (target: <600ms)"

async def main():
    log.info("Starting latency benchmark")
    log.info("=" * 50)

    log.info("Benchmarking question detector...")
    await benchmark_question_detector()

    log.info("Benchmarking LLM TTFT...")
    await benchmark_llm_ttft()

    log.info("=" * 50)
    log.info("All benchmarks PASSED ✓")

if __name__ == "__main__":
    asyncio.run(main())
Antigravity Mission Instructions (Copy-Paste Ready)
Markdown

## MISSION: Execute Phase 0 — Core Pipeline

### Context files to load:
- docs/PROJECT_BRIEF.md
- docs/ARCHITECTURE.md (the full PRD)

### Your task:
Create all files listed in Phase 0 exactly as specified.
Do not modify any architecture decisions.

### Execution order (strict):
1. Create docker-compose.yml, .env.example, backend/requirements.txt
2. Create backend/app/config.py, database.py, main.py
3. Create backend/app/services/stt/base.py, deepgram.py
4. Create backend/app/services/vad.py, question_detector.py
5. Create backend/app/services/llm_router.py, session_manager.py
6. Create backend/app/routers/websocket.py
7. Create frontend/test.html

### Verification (required before marking complete):
1. Terminal: docker-compose up -d
2. Terminal: curl http://localhost:8000/health → must return {"status": "healthy"}
3. Browser: open frontend/test.html
4. Browser: click "Start Recording", speak the phrase:
   "Tell me about a time you handled a difficult situation at work"
5. Verify in browser:
   - Transcript appears within 1s of speaking
   - "QUESTION DETECTED" label appears
   - Answer starts streaming within 2s of silence
6. Terminal: python -m tests.benchmark_latency → all assertions must pass
7. Take a screenshot artifact of the browser showing a complete answer.

### Done criteria:
- All 7 steps above pass
- No secrets in committed files
- No TODO comments left in code
- pytest backend/tests/ passes with 0 failures