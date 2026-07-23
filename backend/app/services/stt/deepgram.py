import asyncio
import time
import structlog
from collections.abc import AsyncGenerator
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
)

from app.config import get_settings
from app.services.stt.base import STTProvider, TranscriptEvent

log = structlog.get_logger()
settings = get_settings()


class DeepgramProvider(STTProvider):
    """
    Deepgram streaming STT with diarization.
    Uses nova-2 model for best accuracy/latency tradeoff.
    Pinned to deepgram-sdk==3.4.0 (fix.md Gap 1.3).
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
        queue: asyncio.Queue[TranscriptEvent | None] = asyncio.Queue()

        connection = self.client.listen.asyncwebsocket.v("1")

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
                log.info("Deepgram transcript emitted", text=event.text, is_final=event.is_final)
                await queue.put(event)
            except Exception as e:
                log.error("Deepgram transcript callback error", error=str(e))

        async def on_error(self_inner, error, **kwargs):  # type: ignore
            log.error("Deepgram error", error=str(error))
            await queue.put(None)

        connection.on(LiveTranscriptionEvents.Transcript, on_transcript)
        connection.on(LiveTranscriptionEvents.Error, on_error)

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
            keywords=[
                "large-scale:2",
                "system design:2",
                "microservices:2",
                "Kubernetes:2",
                "PostgreSQL:2",
                "full-stack:2",
                "scalability:2",
                "architecture:2",
            ],
        )

        started = await connection.start(options)
        if not started:
            raise RuntimeError("Failed to start Deepgram connection")

        log.info("Deepgram connection established")

        # Feed audio in background task
        async def feed_audio() -> None:
            import json
            keepalive_msg = json.dumps({"type": "KeepAlive"})
            try:
                async for chunk in audio_stream:
                    if not chunk:  # b"" keepalive signal from generator
                        try:
                            await connection.send(keepalive_msg)
                        except Exception:
                            pass
                    else:
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
