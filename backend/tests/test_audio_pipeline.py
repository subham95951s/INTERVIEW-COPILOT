import pytest
import numpy as np
from app.services.audio.noise_suppressor import NoiseSuppressor, NoiseSuppressorConfig
from app.services.vad import AdaptiveSileroVAD, VADState
from app.services.audio.diarizer import SimpleSpeakerIdentifier
from app.stealth_overlay import apply_stealth_to_hwnd


def generate_sample_pcm(duration_ms: int = 250, frequency_hz: float = 440.0, amplitude: float = 0.5) -> bytes:
    """Generate sample 16kHz mono int16 PCM audio."""
    samples = int(16000 * (duration_ms / 1000.0))
    t = np.linspace(0, duration_ms / 1000.0, samples, endpoint=False)
    wave = np.sin(2 * np.pi * frequency_hz * t) * amplitude
    pcm = (wave * 32767).astype(np.int16)
    return pcm.tobytes()


def test_noise_suppressor():
    suppressor = NoiseSuppressor(NoiseSuppressorConfig(enabled=True))
    sample = generate_sample_pcm(duration_ms=250, amplitude=0.3)
    cleaned = suppressor.suppress(sample)
    assert isinstance(cleaned, bytes)
    assert len(cleaned) == len(sample)


def test_adaptive_silero_vad():
    orig_load = AdaptiveSileroVAD._load_model
    AdaptiveSileroVAD._load_model = lambda self: None
    try:
        vad = AdaptiveSileroVAD(base_silence_threshold_ms=500)
        state = VADState()

        # Feed low probability to test noise floor adaptation
        vad.update_noise_floor(0.15)
        assert vad._noise_floor == pytest.approx(0.15, abs=0.05)
        thresh = vad.get_adaptive_threshold()
        assert 0.30 <= thresh <= 0.70

        # Feed audio chunk
        sample = generate_sample_pcm(duration_ms=250)
        new_state, end_of_utt = vad.process_chunk(sample, state)
        assert isinstance(new_state, VADState)
        assert isinstance(end_of_utt, bool)
    finally:
        AdaptiveSileroVAD._load_model = orig_load


def test_simple_speaker_identifier():
    identifier = SimpleSpeakerIdentifier()
    interviewer_audio = generate_sample_pcm(250, 440.0, 0.6)
    candidate_audio = generate_sample_pcm(250, 880.0, 0.3)

    success = identifier.calibrate(interviewer_audio, candidate_audio)
    assert success is True

    result = identifier.identify_speaker(interviewer_audio)
    assert result in ("interviewer", "candidate")


def test_stealth_overlay_safe_handle():
    # Calling on invalid window handle 0 should return False cleanly without throwing
    res = apply_stealth_to_hwnd(0)
    assert isinstance(res, bool)
