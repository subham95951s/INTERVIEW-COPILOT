Antigravity Implementation Audit
Gaps, Ambiguities & Exact Instructions Needed
Honest answer: The plan is ~75% bulletproof. The architecture and code are solid, but there are specific gaps that will cause Antigravity to either stall, hallucinate solutions, or produce broken code if you don't address them upfront.

Here is every gap, exactly why it breaks, and the precise instruction to fix it.

Category 1: Hard Blockers
Things that WILL fail without intervention
Gap 1.1 — Silero VAD Torch Hub Download Will Fail in Docker
Why it breaks:

Python

# This line in vad.py:
model, _ = torch.hub.load(
    repo_or_dir="snakers4/silero-vad",
    model="silero_vad",
    force_reload=False,
)
# torch.hub.load() downloads from GitHub at RUNTIME
# Inside Docker with no internet = silent failure or 30s timeout
# The container will start but VAD will be broken with no clear error
The fix — add to Dockerfile:

Dockerfile

# Add this to backend/Dockerfile BEFORE the CMD line

# Pre-download Silero VAD model at build time so it's baked into image
RUN python -c "
import torch
torch.hub.load(
    'snakers4/silero-vad',
    'silero_vad',
    force_reload=True,
    onnx=False
)
print('Silero VAD model cached successfully')
"
Exact Antigravity instruction:

text

IMPORTANT: The Silero VAD model must be downloaded at Docker 
BUILD time, not runtime. Add a RUN python -c "torch.hub.load..." 
command to backend/Dockerfile after pip install but before CMD. 
Verify by running: docker build backend/ and confirming the 
build log shows "Silero VAD model cached successfully" with 
no network errors.
Gap 1.2 — pgvector IVFFlat Index Requires Data Before Creation
Why it breaks:

SQL

-- This in the migration will FAIL on empty table:
CREATE INDEX ON document_chunks 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- IVFFlat requires at least `lists` rows to train on.
-- On an empty fresh database = Postgres error:
-- "ERROR: training set too small"
-- Alembic migration will crash and leave DB in broken state
The fix:

SQL

-- Replace IVFFlat with HNSW for zero-data-required indexing
-- HNSW is actually better for your scale anyway

CREATE INDEX ON document_chunks 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- HNSW works on empty tables, no minimum row requirement
-- Better query performance at < 1M vectors (your entire MVP scale)
-- Only downside: slightly more memory — irrelevant at your scale
Exact Antigravity instruction:

text

CRITICAL: Do NOT use IVFFlat index for the document_chunks 
embedding column. It requires pre-existing data to train on 
and will crash on an empty database. Use HNSW index instead:

CREATE INDEX ON document_chunks 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

This works on empty tables and performs better at our scale.
Apply this in the Alembic initial migration, not as a 
separate migration step.
Gap 1.3 — Deepgram SDK v3 Has Breaking API Changes
Why it breaks:

Python

# The implementation uses Deepgram SDK v3 patterns
# BUT the callback registration syntax changed between v3 minor versions
# AND the asynclive API is different from the live API

# What the plan has:
connection = self.client.listen.asynclive.v("1")

@connection.on(LiveTranscriptionEvents.Transcript)
async def on_transcript(self_inner, result, **kwargs):
    ...

# Common failure: 'self_inner' parameter causes
# "on_transcript() takes 1 positional argument but 2 were given"
# because the SDK passes the connection object as first arg
# This is a known SDK inconsistency across v3.x.x patch versions
The fix — version-pin AND use safer callback pattern:

Python

# In requirements.txt — pin to exact known-working version:
deepgram-sdk==3.4.0  # NOT 3.7.0 — callback API is stable here

# In deepgram.py — safer callback without self_inner:
@connection.on(LiveTranscriptionEvents.Transcript)
async def on_transcript(result, **kwargs):  # Remove self_inner
    try:
        alt = result.channel.alternatives[0]
        ...
Exact Antigravity instruction:

text

Pin deepgram-sdk to version 3.4.0 in requirements.txt.
In the DeepgramProvider callback registration, the callback 
functions should NOT have a self_inner first parameter.
The correct signature is:

    async def on_transcript(result, **kwargs):
    async def on_error(error, **kwargs):

NOT:
    async def on_transcript(self_inner, result, **kwargs):

Verify by running the test.html page and confirming 
transcripts appear. If you see "takes N positional arguments" 
errors in backend logs, the callback signature is wrong.
Gap 1.4 — WebSocket Audio Queue Deadlock Risk
Why it breaks:

Python

# Current implementation in websocket.py:
audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=100)

# The problem:
# 1. process_audio_chunk() calls _question_detector.classify()
#    which is an AWAITED HTTP call to Groq (~100-200ms)
# 2. During that await, the main while loop is BLOCKED
# 3. Audio chunks arriving from the client PILE UP in the queue
# 4. When queue hits maxsize=100 (4096 bytes × 100 = ~25s of audio)
#    the client's WebSocket send will block
# 5. The Deepgram connection times out from lack of audio
# 6. Everything silently breaks

# The fix: process_audio_chunk must never block the receive loop
The fix:

Python

# In websocket.py — restructure to fully async pipeline

@router.websocket("/ws/session/{session_id}")
async def websocket_session(ws: WebSocket, session_id: str) -> None:
    await ws.accept()
    
    audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=500)
    
    # Separate coroutine for VAD+detection — never blocks receive loop
    async def vad_detection_worker() -> None:
        nonlocal vad_state
        while True:
            chunk = await audio_queue.get()
            if chunk is None:
                break
            
            # This await is now in its own coroutine
            # Main receive loop is never blocked
            vad_state, end_of_utterance = _vad.process_chunk(chunk, vad_state)
            
            if end_of_utterance:
                # Fire and forget — don't await generate_answer
                # It will stream back independently
                asyncio.create_task(handle_end_of_utterance(session_id, ws))
    
    # Main loop ONLY does: receive → queue.put → continue
    # Never awaits anything slow
    vad_task = asyncio.create_task(vad_detection_worker())
    stt_task = asyncio.create_task(process_transcripts())
    
    try:
        while True:
            message = await ws.receive()
            if message["type"] == "websocket.disconnect":
                break
            if "bytes" in message and message["bytes"]:
                # Non-blocking put with overflow protection
                try:
                    audio_queue.put_nowait(message["bytes"])
                except asyncio.QueueFull:
                    # Drop oldest chunk rather than blocking
                    audio_queue.get_nowait()
                    audio_queue.put_nowait(message["bytes"])
    finally:
        await audio_queue.put(None)
        vad_task.cancel()
        stt_task.cancel()
Exact Antigravity instruction:

text

ARCHITECTURE REQUIREMENT: The WebSocket receive loop must 
NEVER await slow operations (HTTP calls, LLM generation).

Structure the WebSocket handler as THREE separate async 
coroutines running concurrently via asyncio.create_task():

1. receive_loop: only does ws.receive() → audio_queue.put_nowait()
   Never awaits anything else. Drop chunks if queue full.

2. vad_worker: pulls from audio_queue, runs VAD (fast, sync-ish),
   when end_of_utterance detected → asyncio.create_task(handle_question())

3. stt_processor: feeds audio to Deepgram, handles transcript events

handle_question() is itself a task — it awaits classify() and 
generate_stream() without blocking anything else.

This is the ONLY architecture that avoids queue deadlocks
under real audio load.
Gap 1.5 — Missing Alembic Configuration
Why it breaks:

text

The plan mentions Alembic but provides zero configuration for it.
Antigravity will either:
a) Skip migrations entirely and use SQLAlchemy create_all() 
   (which doesn't create the pgvector extension or HNSW index)
b) Generate broken alembic.ini pointing to wrong database URL
c) Hallucinate a migration that doesn't match your actual models

Without proper Alembic setup, the database schema 
will be missing the vector extension and proper indexes.
The fix — provide exact files:

backend/alembic.ini (critical parts):

ini

[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os

# DO NOT hardcode URL here — read from env
sqlalchemy.url = 
backend/alembic/env.py:

Python

import asyncio
import os
from logging.config import fileConfig
from sqlalchemy import pool, text
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# Import ALL models so Alembic can detect them
from app.models.user import User
from app.models.session import InterviewSession
from app.models.document_chunk import DocumentChunk
# ... all other models

from app.database import Base
from app.config import get_settings

settings = get_settings()
config = context.config

# Override sqlalchemy.url from environment
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        # Enable pgvector BEFORE creating tables
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await connection.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


run_migrations_online()
Exact Antigravity instruction:

text

Create a complete Alembic setup with these requirements:

1. alembic.ini must NOT hardcode the database URL — 
   it must be empty and overridden in env.py from settings

2. alembic/env.py must:
   a) Import ALL SQLAlchemy models before target_metadata
   b) Run "CREATE EXTENSION IF NOT EXISTS vector" BEFORE 
      any table creation — this is required for pgvector columns
   c) Use async_engine_from_config for async SQLAlchemy

3. Generate the initial migration with:
   alembic revision --autogenerate -m "initial_schema"
   Then verify the generated migration contains the vector 
   extension creation and the HNSW index creation.

4. The HNSW index must be added MANUALLY to the migration
   since Alembic cannot auto-detect it:
   op.execute("""
     CREATE INDEX ON document_chunks 
     USING hnsw (embedding vector_cosine_ops)
     WITH (m = 16, ef_construction = 64)
   """)
Category 2: Soft Failures
Things that work initially but break under real use
Gap 2.1 — No Audio Resampling Validation
Why it matters:

text

The browser AudioContext is initialized with sampleRate: 16000
BUT: Not all browsers/OS combinations honor this request.
Chrome on some systems will give you 44100Hz or 48000Hz 
regardless of what you request.

Deepgram configured for 16kHz receiving 44.1kHz audio = 
garbled transcripts that look like random words.
This will waste hours of debugging.
Exact Antigravity instruction:

text

In useAudioCapture.ts, after creating the AudioContext, 
add a validation check:

const audioContext = new AudioContext({ sampleRate: 16000 })

// Validate actual sample rate
if (audioContext.sampleRate !== 16000) {
  console.warn(
    `Browser provided ${audioContext.sampleRate}Hz instead of 16000Hz. 
     Resampling will be applied.`
  )
  // Add offline resampling before sending to WebSocket:
  // Use OfflineAudioContext to resample float32 to 16kHz
  // before converting to Int16 PCM
}

Implement a resampleTo16kHz(float32Buffer, sourceSampleRate) 
helper function using OfflineAudioContext that handles the 
case where the browser does not honor the 16000Hz request.
Add a visible warning banner in the UI if resampling is active.
Gap 2.2 — JWT Token Not Passed to WebSocket
Why it matters:

Python

# Current websocket.py has:
await session_mgr.create_session(
    session_id=session_id,
    user_id="test_user",  # ← THIS IS A PLACEHOLDER
    candidate_name="Candidate",
)

# The plan says "Replace with auth in Phase 2"
# BUT Antigravity will likely leave this placeholder forever
# because it's explicitly marked as a note, not a TODO

# WebSockets cannot use HTTP Authorization headers
# They must use query params or a token exchange pattern
The fix — define the auth pattern explicitly:

Python

# WebSocket URL pattern:
# wss://api/ws/session/{session_id}?token={jwt_access_token}

# In websocket.py:
from fastapi import WebSocket, Query
from jose import jwt, JWTError

@router.websocket("/ws/session/{session_id}")
async def websocket_session(
    ws: WebSocket,
    session_id: str,
    token: str = Query(...),  # JWT passed as query param
) -> None:
    # Validate token before accepting connection
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        user_id = payload.get("sub")
        if not user_id:
            await ws.close(code=4001, reason="Invalid token")
            return
    except JWTError:
        await ws.close(code=4001, reason="Unauthorized")
        return
    
    await ws.accept()
    # Now use real user_id, not "test_user"
Exact Antigravity instruction:

text

WebSocket authentication must be implemented using JWT 
query parameters, NOT HTTP headers (browsers cannot set 
custom headers on WebSocket connections).

Pattern:
  Client connects to: ws://host/ws/session/{id}?token={jwt}
  Server validates token BEFORE calling ws.accept()
  If invalid: ws.close(code=4001) WITHOUT accepting

The user_id="test_user" placeholder must be replaced with 
the actual user_id extracted from the validated JWT token.
This is NOT optional — without this, any user can 
access any other user's session by knowing the session_id.
Gap 2.3 — No CORS for WebSocket + Missing Environment for Production
Why it matters:

text

FastAPI's CORSMiddleware does NOT apply to WebSocket connections.
WebSocket origin validation must be done manually.

In development this doesn't matter (localhost).
In production on Fly.io, a malicious site could connect 
to your WebSocket endpoint from any origin.
Exact Antigravity instruction:

text

Add WebSocket origin validation in websocket.py:

ALLOWED_ORIGINS = settings.cors_origins_list

@router.websocket("/ws/session/{session_id}")
async def websocket_session(ws: WebSocket, ...):
    # Check origin header before accepting
    origin = ws.headers.get("origin", "")
    if settings.is_production and origin not in ALLOWED_ORIGINS:
        await ws.close(code=4003, reason="Origin not allowed")
        return
    
    await ws.accept()
    ...

Also create backend/app/middleware/websocket_auth.py as a 
separate concern so origin validation is not buried in the 
route handler.
Gap 2.4 — RAG Retrieval Returns Nothing for First Question
Why it matters:

Python

# Timeline problem:
# 1. User creates session → POST /sessions
# 2. Server calls rag.ingest_resume() and rag.ingest_jd()
# 3. These embedding calls take 2-5 SECONDS (OpenAI API round trip)
# 4. User immediately starts interview
# 5. First question gets asked during ingestion
# 6. rag.retrieve() returns empty → answer has no resume context
# 7. User gets a generic answer for their first question

# This is a race condition between ingestion and first retrieval
The fix:

Python

# In sessions router — make ingestion status trackable:

# POST /sessions response should include ingestion_status
# Client should poll GET /sessions/{id}/ingestion-status
# InterviewPage should show "Preparing your context..." 
# and disable the Start Recording button until status = "ready"

# In session_manager.py — add ingestion status to Redis:
async def set_ingestion_status(
    self, 
    session_id: str, 
    status: str  # "pending" | "ready" | "failed"
) -> None:
    await self.redis.set(
        f"session:{session_id}:ingestion_status",
        status,
        ex=SESSION_TTL_SECONDS
    )
Exact Antigravity instruction:

text

There is a race condition between document ingestion and 
the first interview question. Fix it with this flow:

1. POST /sessions returns immediately with status="pending"
   and starts ingestion as a background task 
   (use FastAPI BackgroundTasks)

2. Add GET /sessions/{id}/ready endpoint that returns:
   {"ready": bool, "chunks_indexed": int}
   This checks Redis for ingestion completion flag.

3. In InterviewPage.tsx, poll /sessions/{id}/ready every 
   500ms after session creation. Show a loading state:
   "Indexing your resume... (X chunks ready)"
   Disable the Start Recording button until ready=true.

4. In the RAG ingest function, set a Redis key 
   "session:{id}:ingestion_status" = "ready" when complete.

Never allow a recording session to start before 
ingestion_status = "ready".
Gap 2.5 — Groq Rate Limits Will Hit in Development
Why it matters:

text

Groq free tier limits:
  Llama-3.3-70B: 30 requests/minute, 6000 tokens/minute
  Llama-3-8B: 30 requests/minute, 14400 tokens/minute

During development you'll hit these constantly because:
- Question classifier uses Llama-3-8B (every silence > 1s)
- Answer generator uses Llama-3.3-70B (every detected question)
- Running benchmark tests makes rapid sequential calls
- Rate limit errors look like generic 429 errors with no retry

Without retry logic, the entire WebSocket pipeline 
silently fails on rate limit.
Exact Antigravity instruction:

text

Add rate limit handling with exponential backoff to BOTH 
QuestionDetector and all LLM providers using tenacity:

from tenacity import (
    retry, 
    stop_after_attempt, 
    wait_exponential,
    retry_if_exception_type,
)
from groq import RateLimitError

@retry(
    retry=retry_if_exception_type(RateLimitError),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=1, max=30),
)
async def classify(self, transcript_buffer: str) -> ...:
    ...

Additionally, send a WebSocket message to the client 
when rate limiting occurs:
{"type": "status", "message": "Rate limited — retrying...", "code": "rate_limit"}

This prevents users from thinking the app is broken 
when it's just waiting on Groq.
Category 3: Missing Files Antigravity Will Not Generate
Gap 3.1 — No Error Boundary in React
Exact Antigravity instruction:

text

Create frontend/src/components/ErrorBoundary.tsx as a 
React class component error boundary. Wrap the entire 
router in App.tsx with this boundary.

Also create a global error handler for unhandled WebSocket 
errors that shows a toast notification rather than a 
blank screen.
Gap 3.2 — No Environment Validation on Startup
Exact Antigravity instruction:

text

In backend/app/main.py lifespan function, add startup 
validation BEFORE the app accepts requests:

async def validate_environment() -> None:
    errors = []
    
    # Test Deepgram API key
    try:
        client = DeepgramClient(settings.deepgram_api_key)
        # Make a minimal test call
    except Exception:
        errors.append("DEEPGRAM_API_KEY is invalid or unreachable")
    
    # Test Groq API key  
    try:
        groq = AsyncGroq(api_key=settings.groq_api_key)
        await groq.models.list()
    except Exception:
        errors.append("GROQ_API_KEY is invalid")
    
    # Test database connection
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            # Verify pgvector extension
            result = await conn.execute(
                text("SELECT * FROM pg_extension WHERE extname='vector'")
            )
            if not result.fetchone():
                errors.append("pgvector extension not installed")
    except Exception as e:
        errors.append(f"Database unreachable: {e}")
    
    if errors:
        for error in errors:
            log.error("Startup validation failed", error=error)
        raise RuntimeError(f"Environment validation failed: {errors}")
    
    log.info("All environment checks passed")

Call validate_environment() at the START of the lifespan 
function before anything else. This surfaces 
misconfigurations immediately instead of at first API call.
Gap 3.3 — No Transcript Persistence to PostgreSQL
Why it matters:

text

Currently transcripts only go to Redis (4hr TTL).
The POST /sessions/{id}/transcript endpoint exists in the 
plan but there's no code that writes transcript entries 
to the transcript_entries PostgreSQL table.

After 4 hours, all session data is gone.
Feedback reports cannot be generated without the transcript.
Exact Antigravity instruction:

text

In websocket.py, when a transcript_final event is received 
with is_final=True, write to BOTH Redis (for fast access) 
AND PostgreSQL transcript_entries table (for persistence).

Use a background task for the PostgreSQL write so it 
doesn't add latency to the WebSocket response path:

async def persist_transcript_entry(
    session_id: str,
    speaker: str, 
    text: str,
    is_question: bool,
    timestamp_ms: int,
) -> None:
    async with AsyncSessionLocal() as db:
        entry = TranscriptEntry(
            session_id=session_id,
            speaker="interviewer" if speaker == "0" else "candidate",
            text=text,
            timestamp_ms=timestamp_ms,
            is_question=is_question,
        )
        db.add(entry)
        await db.commit()

# In the WebSocket handler:
if event.is_final:
    asyncio.create_task(persist_transcript_entry(...))
    # Also write to Redis for fast retrieval
    await session_mgr.append_transcript(...)
Complete Antigravity Briefing Document
Put this in .antigravity/EXECUTION_RULES.md:

Markdown

# Antigravity Execution Rules
# InterviewCopilot AI — Read before every mission

## HARD RULES (Never violate these)

### Rule 1: Docker Build
Silero VAD model MUST be downloaded at Docker build time.
Add to Dockerfile: RUN python -c "import torch; torch.hub.load('snakers4/silero-vad', 'silero_vad', force_reload=True)"
VERIFY: docker build succeeds with "Silero VAD model cached" in logs.

### Rule 2: Vector Index
NEVER use IVFFlat index for document_chunks.embedding.
ALWAYS use HNSW: CREATE INDEX USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64)

### Rule 3: WebSocket Architecture
The ws.receive() loop MUST NEVER await slow operations.
All slow operations (HTTP calls, LLM generation) run in separate asyncio.create_task().
audio_queue.put_nowait() with drop-on-full is the ONLY acceptable pattern.

### Rule 4: WebSocket Auth
JWT token passed as query parameter: /ws/session/{id}?token={jwt}
Token validated BEFORE ws.accept() is called.
user_id="test_user" placeholder is NOT acceptable in any code that gets committed.

### Rule 5: Ingestion Race Condition
POST /sessions must use BackgroundTasks for ingestion.
GET /sessions/{id}/ready must exist and return ingestion status.
InterviewPage must poll /ready and block recording until ready=true.

### Rule 6: Deepgram Callback Signatures
Deepgram SDK v3.4.0 only.
Callbacks: async def on_transcript(result, **kwargs) — NO self_inner parameter.

### Rule 7: Audio Sample Rate
After AudioContext creation, validate audioContext.sampleRate === 16000.
If not, implement OfflineAudioContext resampling before sending PCM to WebSocket.

### Rule 8: Transcript Persistence
Every transcript_final event writes to BOTH Redis AND PostgreSQL.
PostgreSQL write must be asyncio.create_task() (background, non-blocking).

### Rule 9: Environment Validation
validate_environment() runs at startup lifespan.
Tests Deepgram key, Groq key, DB connection, pgvector extension.
App must REFUSE to start if any check fails.

### Rule 10: Rate Limit Handling
All Groq API calls wrapped in tenacity @retry with RateLimitError retry.
Client receives {"type": "status", "code": "rate_limit"} message when retrying.

## VERIFICATION CHECKLIST
Before marking any mission complete, verify ALL of these:

Backend:
[ ] docker-compose up -d — all 3 services healthy
[ ] curl /health → {"status": "healthy"}
[ ] python -m tests.benchmark_latency → all assertions pass
[ ] pytest backend/tests/ → 0 failures
[ ] docker logs ic_backend → no ERROR lines on startup

Pipeline (requires test.html + mic):
[ ] Speak non-question → no answer generated
[ ] Speak question → answer appears within 2s
[ ] Speak same question twice → second answer references first in context
[ ] Disconnect + reconnect → session recovers

Security:
[ ] .env is in .gitignore
[ ] No API keys in any committed file
[ ] git log --all -p | grep -i "api_key" → zero results
[ ] WebSocket rejects connection without valid JWT

Database:
[ ] SELECT * FROM pg_extension WHERE extname='vector' → returns row
[ ] \d document_chunks → embedding column is vector(1536)
[ ] \d+ document_chunks → hnsw index listed
[ ] After speaking a question: SELECT COUNT(*) FROM transcript_entries → > 0
Priority Order to Fix Before Starting
text

┌─────┬──────────────────────────────────────┬──────────┬──────────────┐
│  #  │ Gap                                  │ Impact   │ Fix Time     │
├─────┼──────────────────────────────────────┼──────────┼──────────────┤
│  1  │ WebSocket deadlock architecture      │ 💀 Fatal │ 30 min       │
│  2  │ Silero VAD Docker download           │ 💀 Fatal │ 5 min        │
│  3  │ IVFFlat on empty DB                  │ 💀 Fatal │ 5 min        │
│  4  │ Deepgram SDK callback signature      │ 💀 Fatal │ 10 min       │
│  5  │ Missing Alembic configuration        │ 🔴 High  │ 45 min       │
│  6  │ JWT not passed to WebSocket          │ 🔴 High  │ 20 min       │
│  7  │ Ingestion race condition             │ 🔴 High  │ 30 min       │
│  8  │ Transcript not persisted to Postgres │ 🟡 Med   │ 20 min       │
│  9  │ Groq rate limit handling             │ 🟡 Med   │ 15 min       │
│ 10  │ Audio sample rate validation         │ 🟡 Med   │ 20 min       │
│ 11  │ Environment startup validation       │ 🟢 Low   │ 25 min       │
│ 12  │ WebSocket CORS origin validation     │ 🟢 Low   │ 10 min       │
│ 13  │ React error boundary                 │ 🟢 Low   │ 15 min       │
└─────┴──────────────────────────────────────┴──────────┴──────────────┘

Total fix time before starting: ~3.5 hours of Antigravity work
Without these fixes: estimated 2-3 days of debugging broken behavior