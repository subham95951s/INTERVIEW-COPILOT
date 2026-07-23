"""
Speech Analytics Engine — Real-time telemetry for candidate pacing and filler word radar.

Analyzes candidate transcripts to compute:
  1. Words Per Minute (WPM) over a rolling window
  2. Pacing status (Optimal: 120-160 WPM, Fast: >165 WPM, Slow: <110 WPM)
  3. Filler word frequency and count ("um", "uh", "like", "basically", etc.)
"""

import re
import time
import structlog
from dataclasses import dataclass, field

log = structlog.get_logger()

FILLER_WORDS = {
    "um",
    "uh",
    "like",
    "basically",
    "literally",
    "actually",
    "you know",
    "sort of",
    "kind of",
    "right",
}


@dataclass
class UtteranceRecord:
    timestamp: float
    word_count: int
    filler_count: int


class SpeechAnalyticsEngine:
    """Tracks candidate speech metrics per session in real time."""

    def __init__(self, window_seconds: float = 30.0) -> None:
        self.window_seconds = window_seconds
        self.utterances: list[UtteranceRecord] = []
        self.total_words: int = 0
        self.total_fillers: int = 0

    def analyze_utterance(self, text: str, timestamp: float | None = None) -> dict:
        """
        Process a new final utterance from the candidate and return current speech telemetry.
        """
        now = timestamp or time.time()
        cleaned = text.strip()
        if not cleaned:
            return self.get_telemetry(now)

        # Count total words
        words = re.findall(r"\b[a-zA-Z']+\b", cleaned.lower())
        word_count = len(words)

        # Count filler words and multi-word filler expressions
        lower_text = cleaned.lower()
        filler_count = 0
        for filler in FILLER_WORDS:
            # Use regex word boundaries for precise matching
            pattern = rf"\b{re.escape(filler)}\b"
            matches = re.findall(pattern, lower_text)
            filler_count += len(matches)

        record = UtteranceRecord(
            timestamp=now,
            word_count=word_count,
            filler_count=filler_count,
        )
        self.utterances.append(record)
        self.total_words += word_count
        self.total_fillers += filler_count

        return self.get_telemetry(now)

    def get_telemetry(self, current_time: float | None = None) -> dict:
        """Calculate WPM and pacing status over the active rolling window."""
        now = current_time or time.time()

        # Filter utterances within window
        window_records = [
            u for u in self.utterances if (now - u.timestamp) <= self.window_seconds
        ]

        if not window_records:
            return {
                "wpm": 0,
                "pacing_status": "optimal",
                "filler_count": self.total_fillers,
                "filler_rate": 0.0,
                "total_words": self.total_words,
            }

        window_words = sum(u.word_count for u in window_records)
        oldest_ts = min(u.timestamp for u in window_records)
        elapsed = max(now - oldest_ts, 5.0)  # avoid division by zero or tiny intervals

        wpm = int((window_words / elapsed) * 60.0)

        if wpm > 165:
            pacing_status = "fast"
        elif wpm < 110 and window_words > 10:
            pacing_status = "slow"
        else:
            pacing_status = "optimal"

        filler_rate = round(
            (self.total_fillers / self.total_words) * 100.0 if self.total_words > 0 else 0.0,
            1,
        )

        return {
            "wpm": wpm,
            "pacing_status": pacing_status,
            "filler_count": self.total_fillers,
            "filler_rate": filler_rate,
            "total_words": self.total_words,
        }
