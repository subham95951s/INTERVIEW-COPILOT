"""
Real-time audio noise suppression service for InterviewCopilot AI.
Applies low-latency noise reduction to incoming 16kHz PCM audio buffers
before passing them to Voice Activity Detection (VAD) and Speech-to-Text (STT).
"""

from dataclasses import dataclass
import numpy as np
import structlog

log = structlog.get_logger()

try:
    import noisereduce as nr
    NOISEREDUCE_AVAILABLE = True
except ImportError:
    NOISEREDUCE_AVAILABLE = False


@dataclass
class NoiseSuppressorConfig:
    enabled: bool = False
    sample_rate: int = 16000
    prop_decrease: float = 0.75
    stationary: bool = False


class NoiseSuppressor:
    """
    Real-time audio noise suppressor processing 16-bit PCM mono frames.
    Removes stationary & non-stationary background hum, fan noise, and clicks.
    """

    def __init__(self, config: NoiseSuppressorConfig | None = None) -> None:
        self.config = config or NoiseSuppressorConfig()
        self._noise_profile: np.ndarray | None = None
        self._samples_collected = 0
        log.info(
            "Initialized NoiseSuppressor",
            enabled=self.config.enabled,
            noisereduce_available=NOISEREDUCE_AVAILABLE,
        )

    def suppress(self, pcm_bytes: bytes) -> bytes:
        """
        Suppress background noise in raw 16-bit PCM mono bytes.
        Returns cleaned PCM bytes. Never raises exceptions.
        """
        if not self.config.enabled or not pcm_bytes:
            return pcm_bytes

        try:
            audio = np.frombuffer(pcm_bytes, dtype=np.int16)
            if len(audio) == 0:
                return pcm_bytes

            audio_float = audio.astype(np.float32) / 32768.0

            # Collect initial silence/background samples for profile (first 0.5 sec)
            if self._noise_profile is None and len(audio_float) >= 4000:
                self._noise_profile = audio_float[:4000]
                log.debug("Calibrated background noise profile")

            if NOISEREDUCE_AVAILABLE:
                reduced = nr.reduce_noise(
                    y=audio_float,
                    sr=self.config.sample_rate,
                    y_noise=self._noise_profile,
                    prop_decrease=self.config.prop_decrease,
                    stationary=self.config.stationary,
                )
                clean_int16 = np.clip(reduced * 32768.0, -32768, 32767).astype(np.int16)
                return clean_int16.tobytes()
            else:
                # Fast spectral gating fallback using simple thresholding/high-pass filtering
                # Removes DC offset and low-level noise floor (< -50 dBFS)
                audio_float = audio_float - np.mean(audio_float)
                noise_gate = 0.005  # ~ -46 dBFS
                gated = np.where(np.abs(audio_float) < noise_gate, audio_float * 0.2, audio_float)
                clean_int16 = np.clip(gated * 32768.0, -32768, 32767).astype(np.int16)
                return clean_int16.tobytes()

        except Exception as e:
            log.warning("Noise suppression bypass due to error", error=str(e))
            return pcm_bytes
