import structlog
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import get_settings
from app.database import engine, init_db
import app.models  # noqa: F401 — ensures all models register with Base.metadata

log = structlog.get_logger()
settings = get_settings()

# Global Redis client
redis_client: aioredis.Redis | None = None


async def validate_environment() -> None:
    """
    Validate all external dependencies at startup.
    App REFUSES to start if any check fails. (fix.md Gap 3.2)
    """
    errors: list[str] = []

    # Test Deepgram API key
    try:
        from deepgram import DeepgramClient
        client = DeepgramClient(settings.deepgram_api_key)
        log.info("Deepgram API key present")
    except Exception:
        errors.append("DEEPGRAM_API_KEY is invalid or missing")

    # Test Groq API key
    try:
        from groq import AsyncGroq
        groq = AsyncGroq(api_key=settings.groq_api_key)
        await groq.models.list()
        log.info("Groq API key validated")
    except Exception:
        errors.append("GROQ_API_KEY is invalid or unreachable")

    # Test database connection + pgvector extension
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            result = await conn.execute(
                text("SELECT * FROM pg_extension WHERE extname='vector'")
            )
            if not result.fetchone():
                errors.append("pgvector extension not installed in database")
            else:
                log.info("Database connected, pgvector extension verified")
    except Exception as e:
        errors.append(f"Database unreachable: {e}")

    if errors:
        for error in errors:
            log.error("Startup validation failed", error=error)
        raise RuntimeError(f"Environment validation failed: {errors}")

    log.info("All environment checks passed")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize and cleanup application resources."""
    global redis_client

    log.info("Starting InterviewCopilot AI backend")

    # Validate environment FIRST (fix.md Gap 3.2)
    await validate_environment()

    # Initialize database tables
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

# CORS (note: does NOT apply to WebSocket — handled manually in websocket.py)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routers lazily to avoid circular imports at module level
from app.routers import auth, resumes, job_descriptions, sessions, websocket  # noqa: E402

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
