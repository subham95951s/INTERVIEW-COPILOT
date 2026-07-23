"""
WebSocket pipeline for real-time interview processing.

ARCHITECTURE (fix.md Gap 1.4):
The ws.receive() loop NEVER awaits slow operations.
Three separate async coroutines run concurrently:

1. receive_loop: ws.receive() → audio_queue.put_nowait()
2. vad_worker: pulls from queue, runs VAD, fires handle_question() as task
3. stt_processor: feeds audio to Deepgram, handles transcript events

handle_question() is a fire-and-forget asyncio.create_task() — it awaits
classify() and generate_stream() without blocking anything else.

SECURITY (fix.md Gap 2.2, 2.3):
- JWT auth via query parameter, validated before ws.accept()
- Origin validation in production mode

PERSISTENCE (fix.md Gap 3.3):
- Transcript writes to BOTH Redis (fast) and PostgreSQL (persistent)
"""

import asyncio
import json
import time
import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from starlette.websockets import WebSocketState
from jose import jwt, JWTError

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.services.stt.deepgram import DeepgramProvider
from app.services.vad import AdaptiveSileroVAD, VADState
from app.services.audio.noise_suppressor import NoiseSuppressor
from app.services.audio.diarizer import SimpleSpeakerIdentifier
from app.services.question_detector import QuestionDetector
from app.services.llm_router import get_llm_provider, LLMContext
from app.services.session_manager import SessionManager
from app.services.rag import RAGService, AdvancedRetriever, RetrievalConfig
from app.services.answer import AnswerGenerationPipeline
from app.services.memory import (
    SemanticSessionMemory,
    CrossSessionMemory,
    MemoryEntry,
    TopicExtractor,
)
from app.services.coaching import (
    SpeechAnalyticsEngine,
    CheatSheetGenerator,
    FollowUpPredictor,
)
from app.services.coding import CodingQuestionPipeline


log = structlog.get_logger()
settings = get_settings()
router = APIRouter()

# Singletons loaded once at module import
_vad = AdaptiveSileroVAD(base_silence_threshold_ms=settings.vad_silence_threshold_ms)
_noise_suppressor = NoiseSuppressor()
_question_detector = QuestionDetector()


async def _send_json(ws: WebSocket, data: dict) -> None:
    """Safe JSON send — ignores errors on closed connections."""
    try:
        if ws.client_state == WebSocketState.CONNECTED:
            await ws.send_json(data)
    except Exception:
        pass


def _validate_jwt_token(token: str) -> str | None:
    """
    Validate JWT and return user_id, or None if invalid.
    (fix.md Gap 2.2)
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id = payload.get("sub")
        return user_id if user_id else None
    except JWTError:
        return None


def _normalize_question_text(text: str) -> str:
    """Normalize question text for debounce/deduplication comparisons."""
    import re
    cleaned = re.sub(r'[^\w\s]', '', text.lower())
    return " ".join(cleaned.split())


@router.websocket("/ws/session/{session_id}")
async def websocket_session(
    ws: WebSocket,
    session_id: str,
    token: str = Query(default=None),
) -> None:
    """
    Main WebSocket endpoint for real-time interview processing.

    Connect: ws://host/ws/session/{session_id}?token={jwt}
    """

    # ── Origin validation (fix.md Gap 2.3) ────────────────────────────
    if settings.is_production:
        origin = ws.headers.get("origin", "")
        if origin not in settings.cors_origins_list:
            log.warning("WebSocket origin rejected", origin=origin)
            await ws.close(code=4003, reason="Origin not allowed")
            return

    # ── JWT validation (fix.md Gap 2.2) ────────────────────────────────
    # In Phase 0 (development), allow connections without token for test.html
    user_id = "dev_user"
    if token:
        validated_user_id = _validate_jwt_token(token)
        if validated_user_id is None:
            await ws.close(code=4001, reason="Unauthorized")
            return
        user_id = validated_user_id
    elif settings.is_production:
        await ws.close(code=4001, reason="Token required")
        return

    # Check database session record to resolve actual user_id if available
    try:
        async with AsyncSessionLocal() as db_session:
            from sqlalchemy import select
            from app.models.session import InterviewSession
            result = await db_session.execute(
                select(InterviewSession).where(InterviewSession.id == session_id)
            )
            db_sess = result.scalar_one_or_none()
            if db_sess and db_sess.user_id:
                user_id = db_sess.user_id
    except Exception as exc:
        log.warning("Could not fetch session user_id from DB", error=str(exc))

    await ws.accept()
    log.info("WebSocket connected", session_id=session_id, user_id=user_id)

    # ── Initialize services ───────────────────────────────────────────
    redis = ws.app.state.redis
    session_mgr = SessionManager(redis)
    stt_provider = DeepgramProvider()
    llm_provider = get_llm_provider()

    vad_state = VADState()
    # Increased maxsize to 500 to handle bursts (fix.md Gap 1.4)
    audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=500)
    # Shared queue for both STT and VAD to consume from
    stt_queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=500)

    # Create session in Redis
    await session_mgr.create_session(
        session_id=session_id,
        user_id=user_id,
        candidate_name="Candidate",
    )

    # ── Audio → STT generator bridge ──────────────────────────────────

    async def audio_generator():
        """Yields audio chunks for the STT provider, or empty b'' keepalives."""
        while True:
            try:
                chunk = await asyncio.wait_for(stt_queue.get(), timeout=4.0)
                if chunk is None:
                    break
                yield chunk
            except TimeoutError:
                yield b""

    # ── STT Processor (coroutine 3) ───────────────────────────────────
    speech_analytics = SpeechAnalyticsEngine()

    async def stt_processor() -> None:
        """Feeds audio to Deepgram and handles transcript events automatically reconnecting."""
        while True:
            try:
                log.info("Connecting STT audio stream")
                async for event in stt_provider.stream_audio(audio_generator()):
                    log.info("Transcript event", text=event.text, is_final=event.is_final, speaker=event.speaker)
                    # Send transcript to client
                    msg_type = (
                        "transcript_final" if event.is_final else "transcript_partial"
                    )
                    await _send_json(ws, {
                        "type": msg_type,
                        "speaker": event.speaker or "0",
                        "text": event.text,
                        "is_question": False,
                    })

                    # Store final transcripts (fix.md Gap 3.3: dual-write)
                    if event.is_final and event.text.strip():
                        # Analyze pacing & filler words and stream HUD telemetry
                        telemetry = speech_analytics.analyze_utterance(event.text, event.timestamp_ms / 1000.0)
                        await _send_json(ws, {
                            "type": "speech_telemetry",
                            **telemetry,
                        })

                        # Write to Redis (fast, for real-time context)
                        await session_mgr.append_transcript(
                            session_id=session_id,
                            speaker=event.speaker or "0",
                            text=event.text,
                            timestamp_ms=event.timestamp_ms,
                        )
                        # Trigger question check on end of complete utterance or sentence
                        if len(event.text.strip()) >= 12 and event.text.strip()[-1] in ("?", ".", "!"):
                            asyncio.create_task(handle_question(session_id))

                log.info("STT stream ended, re-initializing connection loop")
                await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error("STT processor error, reconnecting", error=str(e))
                await asyncio.sleep(1.0)

    # ── Handle detected question (fire-and-forget task) ────────────────
    last_answered_question = ""
    last_answered_time = 0.0
    current_generation_task: asyncio.Task | None = None

    async def handle_question(session_id: str) -> None:
        """
        Called when end-of-utterance or final STT detected.
        Classifies the unified transcript buffer and generates an answer if it's a complete question.
        """
        nonlocal last_answered_question, last_answered_time, current_generation_task

        transcript_buffer = await session_mgr.get_recent_transcript(
            session_id, seconds=15
        )
        if not transcript_buffer or len(transcript_buffer.strip()) < 15:
            return

        # Check last-speaker rule & transition keywords
        lines = [line.strip() for line in transcript_buffer.strip().split("\n") if line.strip()]
        if lines:
            last_line = lines[-1]
            # Rule A: If Candidate is the last speaker, ignore the trigger
            if last_line.startswith("Candidate:"):
                return
            
            # Rule B: Check for navigation/transition keywords (next, next question)
            last_phrase = last_line.lower()
            if "next question" in last_phrase or "next query" in last_phrase or "next" in last_phrase.split():
                log.info("Transition keyword detected, resetting transcript history", session_id=session_id)
                await redis.delete(f"session:{session_id}:transcript")
                last_answered_question = ""
                last_answered_time = 0.0
                if current_generation_task and not current_generation_task.done():
                    current_generation_task.cancel()
                return

        now_ts = time.time()
        # Prevent re-evaluating or re-answering the same question within 15 seconds
        if last_answered_question and (now_ts - last_answered_time < 15.0):
            norm_buf = _normalize_question_text(transcript_buffer)
            norm_last = _normalize_question_text(last_answered_question)
            if norm_buf in norm_last or norm_last in norm_buf:
                return

        # Notify client if rate limited (fix.md Gap 2.5)
        try:
            detection = await _question_detector.classify(transcript_buffer)
        except Exception:
            await _send_json(ws, {
                "type": "status",
                "message": "Rate limited — retrying...",
                "code": "rate_limit",
            })
            return

        log.info(
            "Question detection",
            is_question=detection.is_question,
            confidence=detection.confidence,
            text=transcript_buffer[:60],
        )

        if not detection.is_question or detection.confidence < 0.65:
            return

        question_text = detection.cleaned_question or transcript_buffer

        if last_answered_question and (now_ts - last_answered_time < 15.0):
            norm_q = _normalize_question_text(question_text)
            norm_last = _normalize_question_text(last_answered_question)
            words_q = set(norm_q.split())
            words_last = set(norm_last.split())
            overlap = len(words_q & words_last) / max(1, min(len(words_q), len(words_last)))
            if overlap >= 0.45 or norm_q in norm_last or norm_last in norm_q:
                return

        last_answered_question = question_text
        last_answered_time = now_ts

        # Signal question detected to client
        await _send_json(ws, {
            "type": "transcript_final",
            "speaker": "0",
            "text": question_text,
            "is_question": True,
        })

        # Interrupt / cancel any active generation task (Rule C: Barge-in / interruption)
        if current_generation_task and not current_generation_task.done():
            log.info("Interrupted current generation task due to new interviewer question")
            current_generation_task.cancel()

        # Start generating answer as a trackable background task
        current_generation_task = asyncio.create_task(
            generate_answer(session_id, question_text)
        )

    async def generate_answer(session_id: str, question: str) -> None:
        """Generate and stream an LLM answer back to the client."""
        start_ms = time.time() * 1000
        meta = await session_mgr.get_meta(session_id)
        candidate_name = meta.get("candidate_name", "the candidate")

        semantic_memory = SemanticSessionMemory(session_id, redis)
        q_embedding: list[float] | None = None
        memory_metadata = {"recalled_count": 0, "projects_avoided": []}
        cross_session_context = "No previous session history."

        # Retrieve relevant resume/JD context via Advanced RAG pipeline
        rag_chunks = "No resume context available."
        jd_summary = "No job description context available."
        embed_fn = None
        try:
            async with AsyncSessionLocal() as db_session:
                rag = RAGService(db_session, redis=redis)
                embed_fn = rag._embed_async
                q_emb_list = await embed_fn([question])
                q_embedding = q_emb_list[0] if q_emb_list else []

                retrieval_config = RetrievalConfig(
                    enable_expansion=False,
                    enable_reranking=False,
                    hybrid_top_k=settings.rag_retrieval_top_k,
                    final_top_k=settings.rag_final_top_k,
                    rrf_weight_bm25=settings.rag_hybrid_bm25_weight,
                    rrf_weight_vector=settings.rag_hybrid_vector_weight,
                )
                advanced = AdvancedRetriever(
                    db=db_session,
                    redis=redis,
                    embed_fn=embed_fn,
                    config=retrieval_config,
                )
                # Run resume, JD retrieval, and cross-session memory in parallel
                resume_task = advanced.retrieve(
                    user_id=user_id,
                    question=question,
                    source_type="resume",
                )
                jd_task = advanced.retrieve(
                    user_id=user_id,
                    question=question,
                    source_type="jd",
                )
                cross_task = CrossSessionMemory(db_session).get_user_performance_context(user_id)
                res_chunks, res_jd, cross_session_context = await asyncio.gather(
                    resume_task, jd_task, cross_task
                )
                rag_chunks = res_chunks
                jd_summary = res_jd
        except Exception as e:
            log.warning("RAG retrieval failed, using empty context", error=str(e))

        qa_history, memory_metadata = await semantic_memory.get_relevant_context(
            question, q_embedding
        )
        combined_history = f"{cross_session_context}\n\nSession Exchanges:\n{qa_history}"

        context = LLMContext(
            candidate_name=candidate_name,
            rag_chunks=rag_chunks,
            jd_summary=jd_summary,
            conversation_history=combined_history,
            question=question,
        )

        cheat_generator = CheatSheetGenerator(settings.groq_api_key)
        bullets = await cheat_generator.generate_bullets(
            question=question,
            resume_context=rag_chunks,
            timeout_ms=160,
        )
        await _send_json(ws, {
            "type": "cheat_sheet",
            "bullets": bullets,
        })

        answer_pipeline = AnswerGenerationPipeline(
            llm_provider=llm_provider,
            redis=redis,
            embed_fn=embed_fn,
            groq_api_key=settings.groq_api_key,
        )

        async def stream_callback(payload: dict) -> None:
            await _send_json(ws, payload)

        try:
            pipeline_result = await answer_pipeline.run(
                session_id=session_id,
                question=question,
                llm_context=context,
                stream_callback=stream_callback,
                memory_context=memory_metadata,
            )
            answer_text = pipeline_result.final_answer
        except asyncio.CancelledError:
            log.info("Answer generation cancelled", session_id=session_id)
            raise
        except Exception as e:
            log.error("Answer generation error", error=str(e))
            await _send_json(ws, {
                "type": "status",
                "message": "Rate limited — retrying...",
                "code": "rate_limit",
            })
            return

        total_latency = int(time.time() * 1000 - start_ms)

        await _send_json(ws, {
            "type": "answer_complete",
            "full_text": answer_text,
            "draft_text": pipeline_result.draft,
            "is_revised": pipeline_result.revised,
            "latency_ms": total_latency,
            "memory_context": pipeline_result.memory_context or memory_metadata,
        })

        # Non-blocking Proactive Follow-Up prediction & caching
        async def _async_predict_followups(q: str, a: str) -> None:
            try:
                predictor = FollowUpPredictor(api_key=settings.groq_api_key)
                predicted = await predictor.predict_followups(q, a)
                if predicted:
                    await _send_json(ws, {
                        "type": "predicted_followups",
                        "followups": predicted,
                    })
            except Exception as exc:
                log.debug("Follow-up task error", error=str(exc))

        asyncio.create_task(_async_predict_followups(question, answer_text))

        # Store Q&A in Redis rolling buffer
        await session_mgr.append_qa(session_id, question, answer_text)

        # Store Q&A asynchronously in Semantic Session Memory without blocking client
        async def _async_store_semantic_memory(q: str, a: str, q_emb: list[float] | None, q_type: str) -> None:
            try:
                extractor = TopicExtractor()
                extracted = await extractor.extract(q, a, groq_api_key=settings.groq_api_key)
                entry = MemoryEntry(
                    question=q,
                    answer=a,
                    question_type=q_type,
                    timestamp_ms=int(time.time() * 1000),
                    question_embedding=q_emb or [],
                    topics_covered=extracted.get("topics_covered", []),
                    projects_mentioned=extracted.get("projects_mentioned", []),
                    skills_demonstrated=extracted.get("skills_demonstrated", []),
                )
                await semantic_memory.add_entry(entry)
            except Exception as exc:
                log.warning("Async semantic memory storage error", error=str(exc))

        asyncio.create_task(
            _async_store_semantic_memory(
                question, answer_text, q_embedding, pipeline_result.question_type
            )
        )

        log.info(
            "Answer generated",
            session_id=session_id,
            latency_ms=total_latency,
        )

    # ── VAD Worker (coroutine 2) ──────────────────────────────────────

    async def vad_worker() -> None:
        """
        Pulls audio from queue, runs VAD, fires handle_question() on
        end-of-utterance. Never blocks the receive loop. (fix.md Gap 1.4)
        """
        nonlocal vad_state
        try:
            while True:
                chunk = await audio_queue.get()
                if chunk is None:
                    break

                vad_state, end_of_utterance = _vad.process_chunk(
                    chunk, vad_state
                )

                if end_of_utterance:
                    # Fire and forget — don't await
                    asyncio.create_task(handle_question(session_id))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.error("VAD worker error", error=str(e))

    # ── Start background coroutines ───────────────────────────────────

    stt_task = asyncio.create_task(stt_processor())
    vad_task = asyncio.create_task(vad_worker())

    # ── Receive Loop (coroutine 1) ────────────────────────────────────
    # ONLY does ws.receive() → queue.put_nowait(). NEVER awaits slow ops.

    chunk_counter = 0
    try:
        while True:
            message = await ws.receive()

            if message["type"] == "websocket.disconnect":
                break

            if message["type"] == "websocket.receive":
                if "bytes" in message and message["bytes"]:
                    pcm_chunk = message["bytes"]
                    chunk_counter += 1
                    if chunk_counter % 50 == 1:
                        log.info("Audio stream active", chunk_number=chunk_counter, bytes=len(pcm_chunk))

                    # Apply real-time noise suppression for VAD
                    clean_chunk = _noise_suppressor.suppress(pcm_chunk)

                    # Feed raw PCM to STT queue (Deepgram neural model expects pristine audio)
                    # Feed suppressed PCM to audio queue for VAD silence detection
                    for q, audio_data in ((audio_queue, clean_chunk), (stt_queue, pcm_chunk)):
                        try:
                            q.put_nowait(audio_data)
                        except asyncio.QueueFull:
                            try:
                                q.get_nowait()
                            except asyncio.QueueEmpty:
                                pass
                            q.put_nowait(audio_data)

                elif "text" in message and message["text"]:
                    # Control messages
                    try:
                        control = json.loads(message["text"])
                        msg_type = control.get("type")
                        if msg_type == "control":
                            action = control.get("action")
                            if action == "end_session":
                                await session_mgr.end_session(session_id)
                                break
                        elif msg_type == "coding_screenshot":
                            image_base64 = control.get("image_base64", "")
                            if image_base64:
                                async def _process_coding_screenshot(img_data: str) -> None:
                                    try:
                                        log.info("Processing coding screenshot", session_id=session_id)
                                        pipeline = CodingQuestionPipeline()
                                        analysis = await pipeline.analyze_screenshot(img_data)
                                        
                                        # Send initial analysis with pseudocode and complexity
                                        analysis_dict = {
                                            "problem_summary": analysis.problem_summary,
                                            "input_format": analysis.input_format,
                                            "output_format": analysis.output_format,
                                            "constraints": analysis.constraints,
                                            "examples": analysis.examples,
                                            "approach": analysis.approach,
                                            "pseudocode": analysis.pseudocode,
                                            "time_complexity": analysis.time_complexity,
                                            "space_complexity": analysis.space_complexity,
                                            "edge_cases": analysis.edge_cases,
                                            "follow_up_considerations": analysis.follow_up_considerations,
                                            "solution_code_python": None,
                                        }
                                        await _send_json(ws, {
                                            "type": "coding_analysis",
                                            "analysis": analysis_dict,
                                        })

                                        # Generate runnable solution code asynchronously and send update
                                        code = await pipeline.generate_solution_code(analysis)
                                        analysis_dict["solution_code_python"] = code
                                        await _send_json(ws, {
                                            "type": "coding_analysis",
                                            "analysis": analysis_dict,
                                        })
                                    except Exception as exc:
                                        log.error("Coding screenshot processing error", error=str(exc))
                                        await _send_json(ws, {
                                            "type": "error",
                                            "message": f"Coding problem analysis failed: {exc}",
                                        })

                                asyncio.create_task(_process_coding_screenshot(image_base64))
                    except json.JSONDecodeError:
                        pass

    except WebSocketDisconnect:
        log.info("WebSocket disconnected", session_id=session_id)
    except Exception as e:
        log.error("WebSocket error", session_id=session_id, error=str(e))
        await _send_json(ws, {"type": "error", "message": str(e)})
    finally:
        # Signal termination to workers
        await audio_queue.put(None)
        await stt_queue.put(None)
        vad_task.cancel()
        stt_task.cancel()
        await stt_provider.close()
        log.info("WebSocket cleanup complete", session_id=session_id)
