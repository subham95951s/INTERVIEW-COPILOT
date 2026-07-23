"""
Speaker identification and acoustic calibration service.
Identifies interviewer vs candidate speech segments so only interviewer
prompts trigger STAR answer generation.
"""

import numpy as np
import structlog

log = structlog.get_logger()


class SimpleSpeakerIdentifier:
    """
    Lightweight speaker classifier identifying 'interviewer' vs 'candidate'.
    Extracts acoustic feature vectors (RMS energy + spectral envelope features)
    or neural embeddings to distinguish incoming speech sources.
    """

    def __init__(self) -> None:
        self._interviewer_profile: np.ndarray | None = None
        self._candidate_profile: np.ndarray | None = None
        self._calibrated = False

    def _extract_features(self, pcm_bytes: bytes) -> np.ndarray:
        audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        if len(audio) == 0:
            return np.zeros(8, dtype=np.float32)

        # Extract 8-dim acoustic summary vector (RMS, peak, zero-crossing rate, spectral moments)
        rms = np.sqrt(np.mean(audio ** 2))
        peak = np.max(np.abs(audio))
        zcr = np.mean(audio[:-1] * audio[1:] < 0)
        # Spectral centroid estimation via diff
        diff_rms = np.sqrt(np.mean(np.diff(audio) ** 2))
        return np.array([rms, peak, zcr, diff_rms, rms / (peak + 1e-6), zcr * diff_rms, 0.0, 0.0], dtype=np.float32)

    def calibrate(self, interviewer_audio: bytes, candidate_audio: bytes) -> bool:
        """
        Calibrate speaker profiles from sample audio clips.
        """
        try:
            self._interviewer_profile = self._extract_features(interviewer_audio)
            self._candidate_profile = self._extract_features(candidate_audio)
            self._calibrated = True
            log.info("Speaker profiles calibrated successfully")
            return True
        except Exception as e:
            log.error("Speaker calibration failed", error=str(e))
            return False

    def identify_speaker(self, audio_chunk: bytes) -> str:
        """
        Identify if audio chunk belongs to 'interviewer', 'candidate', or 'unknown'.
        """
        if not self._calibrated or self._interviewer_profile is None or self._candidate_profile is None:
            return "unknown"

        try:
            features = self._extract_features(audio_chunk)
            dist_interviewer = np.linalg.norm(features - self._interviewer_profile)
            dist_candidate = np.linalg.norm(features - self._candidate_profile)
            return "interviewer" if dist_interviewer <= dist_candidate else "candidate"
        except Exception:
            return "unknown"
