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
