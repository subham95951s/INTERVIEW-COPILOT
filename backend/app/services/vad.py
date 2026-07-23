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
    Model is pre-downloaded at Docker build time (fix.md Gap 1.1).
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
                trust_repo=True,
            )
            self._model = model
            self._model.eval()
            log.info("Silero VAD model loaded")
        except Exception as e:
            log.warning("Could not load Silero VAD from torch.hub, using RMS energy VAD fallback", error=str(e))
            self._model = None

    def get_speech_probability(self, pcm_bytes: bytes) -> float:
        """
        Get probability that the audio chunk contains speech.
        Input: 250ms of 16kHz mono PCM (int16 bytes)
        Output: float in [0, 1]
        """
        try:
            audio_array = np.frombuffer(pcm_bytes, dtype=np.int16)
            if len(audio_array) == 0:
                return 0.0
            audio_float = audio_array.astype(np.float32) / 32768.0

            if self._model is None:
                # RMS energy VAD fallback when neural model is unavailable
                rms = float(np.sqrt(np.mean(audio_float ** 2)))
                return float(min(1.0, max(0.0, (rms - 0.01) * 8.0)))

            tensor = torch.from_numpy(audio_float)

            probs = []
            with torch.no_grad():
                for i in range(0, tensor.shape[0], 512):
                    chunk = tensor[i:i+512]
                    if chunk.shape[0] < 512:
                        chunk = torch.nn.functional.pad(chunk, (0, 512 - chunk.shape[0]))
                    prob = self._model(chunk, SAMPLE_RATE).item()
                    probs.append(prob)

            return float(max(probs)) if probs else 0.0
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


class AdaptiveSileroVAD(SileroVAD):
    """
    Enhanced VAD with:
    1. Adaptive speech threshold based on ambient noise floor estimation.
    2. Dynamic end-of-utterance silence duration based on speech length.
    """

    def __init__(self, base_silence_threshold_ms: int = 1000) -> None:
        super().__init__(silence_threshold_ms=base_silence_threshold_ms)
        self.base_threshold_ms = base_silence_threshold_ms
        self._speech_history: list[float] = []
        self._noise_floor: float = 0.10

    def update_noise_floor(self, prob: float) -> None:
        """Estimate rolling noise floor from low speech probability frames."""
        if prob < 0.30:
            self._speech_history.append(prob)
            if len(self._speech_history) > 100:
                self._speech_history.pop(0)
            if self._speech_history:
                self._noise_floor = float(np.mean(self._speech_history))

    def get_adaptive_threshold(self) -> float:
        """
        Adapt speech probability threshold based on background noise:
        - Noisy environment -> higher threshold to avoid false positives
        - Quiet environment -> lower threshold to catch soft speech
        """
        return max(0.30, min(0.70, self._noise_floor * 2.0))

    def process_chunk(
        self,
        pcm_bytes: bytes,
        state: VADState,
        speech_threshold: float | None = None,
    ) -> tuple[VADState, bool]:
        now_ms = time.time() * 1000
        prob = self.get_speech_probability(pcm_bytes)
        self.update_noise_floor(prob)

        effective_threshold = speech_threshold if speech_threshold is not None else self.get_adaptive_threshold()
        end_of_utterance = False

        if prob >= effective_threshold:
            state.is_speaking = True
            state.silence_start_ms = None
            state.last_speech_ms = now_ms
            state.speech_buffer.append(pcm_bytes)
        else:
            if state.is_speaking:
                if state.silence_start_ms is None:
                    state.silence_start_ms = now_ms

                silence_ms = now_ms - state.silence_start_ms
                speech_duration = now_ms - (state.last_speech_ms or now_ms)

                adaptive_silence = self.base_threshold_ms
                if speech_duration > 10000:
                    adaptive_silence = 1500  # Longer wait after long speech
                elif speech_duration < 2000:
                    adaptive_silence = 700   # Quicker detection for short speech

                if silence_ms >= adaptive_silence:
                    end_of_utterance = True
                    state.is_speaking = False
                    state.silence_start_ms = None
                    state.speech_buffer = []

        return state, end_of_utterance

