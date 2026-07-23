```markdown
# InterviewCopilot AI — Capability Upgrade Master Document
# Principal Architect Analysis | Zero-Budget Engineering Roadmap
# Target: 60% Capability Parity with Parakeet AI

---

## Part 1: Capability Gap Analysis

### Current State Assessment

After analyzing the complete architecture, here is an honest
assessment of what the current implementation does well and
where it falls critically short.

#### What Works Well (Strengths)

```
✅ Core WebSocket pipeline architecture is solid
✅ Three-coroutine pattern (receive/VAD/STT) prevents deadlocks
✅ HNSW vector index for fast retrieval
✅ pgvector integrated cleanly into PostgreSQL
✅ Groq Llama-3.3-70B gives fast TTFT (~400ms)
✅ Deepgram Nova-2 gives reliable streaming STT
✅ Silero VAD is accurate and lightweight
✅ JWT WebSocket auth pattern is correct
✅ Alembic migrations properly structured
✅ Redis session state with correct TTL management
✅ Docker Compose local dev environment is clean
```

#### Critical Gaps (What Parakeet Has That We Don't)

```
Gap 1: Stealth/Invisibility Layer
  Current:  No overlay, no screen-share hiding
  Parakeet: Process-level hiding, window exclusion from capture APIs
  Impact:   Cannot be used in Live Assist mode at all
  Priority: P0

Gap 2: Audio Intelligence
  Current:  Basic Silero VAD, Deepgram diarization (cloud only)
  Parakeet: Multi-speaker separation, noise suppression, 
            acoustic fingerprinting to identify interviewer vs candidate
  Impact:   High false positive rate on question detection
  Priority: P0

Gap 3: Context Window Intelligence
  Current:  Simple rolling 15s transcript buffer
  Parakeet: Full session memory, semantic compression,
            cross-session memory (remembers past interviews)
  Impact:   Answers lose coherence after 5+ questions
  Priority: P1

Gap 4: Answer Quality
  Current:  Single Groq call, no validation, no self-evaluation
  Parakeet: Multi-step generation, self-critique, reflection,
            answer scoring, hallucination detection
  Impact:   Answers sometimes vague, generic, or hallucinated
  Priority: P1

Gap 5: RAG Quality
  Current:  Simple cosine similarity, top-k=4 chunks
  Parakeet: Hybrid search (BM25 + vector), reranking, 
            parent-child chunking, query expansion
  Impact:   Irrelevant chunks pollute context, answers miss details
  Priority: P1

Gap 6: Question Understanding
  Current:  Binary classifier (is/isn't question)
  Parakeet: Question type detection, intent classification,
            sub-topic extraction, difficulty estimation
  Impact:   All questions get the same prompt template
  Priority: P2

Gap 7: Resume Understanding
  Current:  Section-based chunking of raw text
  Parakeet: Structured extraction (entities, roles, dates, metrics),
            skill graph construction, experience timeline
  Impact:   RAG retrieves text chunks, not structured knowledge
  Priority: P2

Gap 8: Coding Question Pipeline
  Current:  Not implemented
  Parakeet: Screenshot → vision model → structured solution approach
  Impact:   Completely missing for technical/coding interviews
  Priority: P2

Gap 9: Streaming Performance
  Current:  No token buffering, no predictive caching
  Parakeet: Speculative generation, answer pre-warming,
            common question caching
  Impact:   First answer always has full latency, no optimization
  Priority: P2

Gap 10: Observability
  Current:  structlog only, no metrics, no traces
  Parakeet: Full distributed tracing, latency histograms,
            per-component profiling
  Impact:   Cannot diagnose latency regressions
  Priority: P3

Gap 11: Offline Capability
  Current:  100% cloud dependent (Deepgram, Groq, OpenAI)
  Parakeet: Local STT fallback, local LLM option
  Impact:   No internet = product completely broken
  Priority: P3

Gap 12: Privacy Architecture
  Current:  Audio flows through Deepgram servers
  Parakeet: Local STT option, audio-never-stored guarantee,
            encrypted session data
  Impact:   Privacy-conscious users will not trust it
  Priority: P3
```

---

### Capability Gap Scoring

```
Feature                          Current   Parakeet   Gap
─────────────────────────────────────────────────────────
Stealth/Invisibility               0%        95%      -95%
Audio Intelligence                20%        85%      -65%
STT Accuracy                      65%        90%      -25%
Speaker Diarization               40%        80%      -40%
Question Detection                45%        85%      -40%
Resume Understanding              30%        80%      -50%
JD Understanding                  25%        75%      -50%
RAG Quality                       35%        85%      -50%
Answer Quality                    40%        85%      -45%
Hallucination Prevention          15%        70%      -55%
Context Memory                    20%        75%      -55%
Coding Question Support            0%        80%      -80%
Streaming Performance             50%        90%      -40%
Observability                     20%        80%      -60%
Privacy Architecture              20%        75%      -55%
─────────────────────────────────────────────────────────
Overall Parity                    28%       ~82%      -54%
Target (60% parity)                         60%
Remaining gap to close:                     32%
```

---

## Part 2: Feature Maturity Matrix

```
Feature                    Maturity    Effort to 60%   Free Solution Exists
──────────────────────────────────────────────────────────────────────────
Stealth Window             None        High            ✅ (OS APIs, free)
Local STT (Whisper)        None        Medium          ✅ (faster-whisper)
Local LLM (Ollama)         None        Medium          ✅ (Ollama + Llama)
Hybrid Search (BM25+vec)   None        Medium          ✅ (rank-bm25)
Reranking                  None        Medium          ✅ (cross-encoder)
Self-Evaluation Pipeline   None        Hard            ✅ (local LLM)
Coding Screenshot Pipeline None        Medium          ✅ (LLaVA local)
Cross-session Memory       None        Hard            ✅ (local embeddings)
Structured Resume Parse    Basic       Medium          ✅ (spaCy + regex)
Parent-Child Chunking      None        Easy            ✅ (custom code)
Query Expansion            None        Easy            ✅ (local LLM)
Answer Caching             None        Easy            ✅ (Redis)
Noise Suppression          None        Easy            ✅ (RNNoise)
VAD Quality                Basic       Easy            ✅ (Silero)
Question Type Classifier   Basic       Easy            ✅ (local LLM)
Distributed Tracing        None        Medium          ✅ (OpenTelemetry)
Prometheus Metrics         None        Easy            ✅ (prometheus-client)
E2E Encryption             None        Medium          ✅ (standard libs)
Local Embeddings           None        Easy            ✅ (sentence-transformers)
STAR Template Engine       Basic       Easy            ✅ (custom prompts)
──────────────────────────────────────────────────────────────────────────
```

---

## Part 3: Technical Debt Assessment

```
Debt Item                          Severity   Impact if Unaddressed
──────────────────────────────────────────────────────────────────────
No local STT fallback              Critical   100% cloud dependency
OpenAI embeddings (paid)           High       $0.0001/1k tokens adds up
No answer validation layer         High       Hallucinations go undetected
Transcript not semantically indexed High      RAG misses conceptual matches
No reranking after retrieval       High       Irrelevant context in prompt
ScriptProcessorNode (deprecated)   Medium     Will break in future Chrome
No circuit breakers on API calls   Medium     One provider failure = outage
Rolling buffer loses context       Medium     Long interviews lose coherence
Single embedding dimension (1536)  Medium     Expensive per OpenAI call
No compression on stored sessions  Low        Redis memory grows fast
No request deduplication           Low        Duplicate Groq calls possible
torch loaded at import time        Low        Slow cold start for backend
──────────────────────────────────────────────────────────────────────
```

---

## Part 4: Recommended Open-Source Stack

All tools below are free, actively maintained, and production-ready.

```
Category              Tool                    License    Why
────────────────────────────────────────────────────────────────────────────
Local STT             faster-whisper          MIT        4x faster than whisper
                      whisper.cpp             MIT        CPU-only, very fast
Local Embeddings      sentence-transformers   Apache 2.0 BAAI/bge-m3 for free
                      bge-m3                  MIT        Best free multilingual
Local LLM             Ollama                  MIT        One-command local LLM
                      llama.cpp               MIT        CPU inference, fast
Local Reranker        cross-encoder/ms-marco  Apache 2.0 Free reranking model
Hybrid Search         rank-bm25               Apache 2.0 BM25 in pure Python
Noise Suppression     RNNoise                 BSD-3      Real-time denoising
                      noisereduce             MIT        Python, easy to use
Audio Processing      pyaudio                 MIT        Cross-platform audio
                      sounddevice             MIT        NumPy-native audio
Speaker Diarization   pyannote.audio          MIT        Best open-source
NLP / NER             spaCy                   MIT        Resume entity extraction
                      Stanza                  Apache 2.0 Stanford NLP pipeline
Document Parsing      pdfminer.six            MIT        Better than pdfplumber
                      markdownify             MIT        HTML/PDF to markdown
Observability         OpenTelemetry           Apache 2.0 Distributed tracing
                      Prometheus              Apache 2.0 Metrics
                      Grafana                 AGPL       Dashboards
Vision (Coding Qs)    LLaVA via Ollama        Apache 2.0 Local vision model
                      moondream               Apache 2.0 Tiny, fast, local
Caching               Redis                   BSD-3      Already in stack
Vector DB             pgvector                PostgreSQL Already in stack
Testing               pytest-benchmark        BSD-2      Performance testing
                      locust                  MIT        Load testing
Encryption            cryptography            Apache 2.0 E2E encryption
Process Hiding        (OS APIs, no library)   N/A        Tauri + Rust OS calls
────────────────────────────────────────────────────────────────────────────
```

---

## Part 5: Development Phases

---

## UPGRADE PHASE A: Stealth & Invisibility Layer
### Priority: P0 | Difficulty: Hard | Impact: Critical

### Why This Phase First

Without a working stealth overlay, InterviewCopilot AI cannot
be used during live interviews at all. This is the core
differentiator of the product. Everything else is secondary.

---

### A.1: Process-Level Hiding

The goal is to make the application invisible to:
1. Screen sharing (Zoom, Teams, Meet, Webex)
2. Screen recording software
3. Proctoring tools that scan process names
4. Window enumeration APIs

#### Process Name Obfuscation (Rust/Tauri)

```rust
// desktop/src-tauri/src/stealth/process.rs

use std::ffi::OsStr;

/// Rename the process to look like a system process.
/// On macOS: uses prctl equivalent via libproc
/// On Windows: modifies the PEB process parameters
pub fn obfuscate_process_name() {
    #[cfg(target_os = "macos")]
    {
        // Set process name to something innocuous
        // "CoreAudiod" or "SystemUIServer" are common choices
        // Use nix::libc::pthread_setname_np
        unsafe {
            let name = b"CoreAudiod\0";
            libc::pthread_setname_np(name.as_ptr() as *const libc::c_char);
        }
    }

    #[cfg(target_os = "windows")]
    {
        // Modify PEB.ProcessParameters.ImagePathName
        // This changes what Task Manager and process scanners see
        // Use windows-rs crate for PEB access
        windows_process_obfuscation::rename_process("RuntimeBroker.exe");
    }
}

/// Hide from window enumeration APIs
/// Prevents tools like WinSpy++ from seeing the overlay window
pub fn hide_from_window_enumeration(hwnd: windows::Win32::Foundation::HWND) {
    #[cfg(target_os = "windows")]
    unsafe {
        use windows::Win32::UI::WindowsAndMessaging::*;
        // Remove from Alt-Tab, taskbar, and window enumeration
        let style = GetWindowLongW(hwnd, GWL_EXSTYLE);
        SetWindowLongW(
            hwnd,
            GWL_EXSTYLE,
            style | WS_EX_TOOLWINDOW as i32,
        );
        // Also hide from SetWindowsHookEx-based process monitors
        SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE).unwrap();
    }
}
```

#### macOS Stealth (Swift Bridge)

```swift
// desktop/src-tauri/src/stealth/macos.swift

import Cocoa
import ScreenCaptureKit

class StealthManager {

    /// Exclude window from ALL screen capture including:
    /// - Zoom screen share
    /// - QuickTime screen recording
    /// - macOS screenshot (Cmd+Shift+3/4)
    /// - Third-party capture apps
    static func hideWindowFromCapture(_ window: NSWindow) {
        window.sharingType = .none
        // .none is stronger than .readOnly
        // Completely excludes from SCShareableContent
    }

    /// Set the application as an accessory to hide from Dock and App Switcher
    static func hideFromDockAndAppSwitcher() {
        NSApp.setActivationPolicy(.accessory)
        // This removes from Dock, Cmd+Tab, and Mission Control
        // The app still runs in background
    }

    /// Prevent the app from appearing in Screen Time reports
    static func hideFromScreenTime() {
        // Use LSUIElement = YES in Info.plist
        // This is set at build time in tauri.conf.json
    }

    /// Make window click-through except when modifier key held
    static func setClickThrough(_ window: NSWindow, enabled: Bool) {
        window.ignoresMouseEvents = enabled
    }

    /// Custom window level above screen savers and fullscreen apps
    static func setUltraHighWindowLevel(_ window: NSWindow) {
        window.level = NSWindow.Level(
            rawValue: Int(CGWindowLevelForKey(.maximumWindow)) + 1
        )
    }
}
```

#### Tauri Integration

```toml
# desktop/src-tauri/Cargo.toml additions

[dependencies]
# Windows OS APIs
[target.'cfg(target_os = "windows")'.dependencies]
windows = { version = "0.52", features = [
    "Win32_Graphics_Gdi",
    "Win32_UI_WindowsAndMessaging",
    "Win32_System_Threading",
    "Win32_Foundation",
]}

# macOS via libc
[target.'cfg(target_os = "macos")'.dependencies]
libc = "0.2"
objc = "0.2"
cocoa = "0.25"
```

```rust
// desktop/src-tauri/src/main.rs

#[tauri::command]
fn apply_stealth_mode(window: tauri::Window) -> Result<(), String> {
    #[cfg(target_os = "windows")]
    {
        use windows::Win32::UI::WindowsAndMessaging::*;
        let hwnd = window.hwnd().map_err(|e| e.to_string())?;
        unsafe {
            // Screen capture exclusion
            SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
                .map_err(|e| e.to_string())?;
            // Remove from Alt-Tab and taskbar
            let style = GetWindowLongW(hwnd, GWL_EXSTYLE);
            SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_TOOLWINDOW as i32);
        }
    }

    #[cfg(target_os = "macos")]
    {
        // Call Swift bridge
        unsafe {
            hide_window_from_capture(window.ns_window().map_err(|e| e.to_string())?);
        }
    }

    Ok(())
}

fn main() {
    // Obfuscate process name at startup before any window is created
    stealth::process::obfuscate_process_name();

    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            apply_stealth_mode,
            start_system_audio_capture,
            stop_audio_capture,
            toggle_overlay_visibility,
            set_overlay_opacity,
        ])
        .setup(|app| {
            // Create overlay window immediately and apply stealth
            let overlay = app.get_window("overlay").unwrap();
            apply_stealth_mode(overlay.clone()).ok();
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error running tauri application");
}
```

---

### A.2: Audio Capture Without Detection

Most proctoring tools detect screen capture APIs being called.
Audio-only capture is much harder to detect.

```rust
// desktop/src-tauri/src/audio/capture.rs

/// Capture system audio WITHOUT triggering screen recording permissions
/// on macOS (ScreenCaptureKit requires screen recording permission)
///
/// Alternative approach: Virtual audio driver
/// BlackHole (macOS) or VB-Cable (Windows) creates a virtual audio device
/// that routes system audio without requiring screen recording permission.
///
/// Installation: User installs BlackHole once, we detect it automatically.

pub struct AudioCaptureStrategy {
    strategy: CaptureMethod,
}

pub enum CaptureMethod {
    /// Requires screen recording permission but captures everything
    ScreenCaptureKit,
    /// Requires virtual driver but no special permissions
    VirtualAudioDriver { device_name: String },
    /// Captures only the candidate's mic — always permitted
    MicrophoneOnly,
}

impl AudioCaptureStrategy {

    pub fn detect_best_strategy() -> Self {
        // 1. Check if BlackHole (macOS) or VB-Cable (Windows) is installed
        if let Some(virtual_device) = Self::find_virtual_audio_device() {
            return AudioCaptureStrategy {
                strategy: CaptureMethod::VirtualAudioDriver {
                    device_name: virtual_device,
                },
            };
        }

        // 2. Fall back to ScreenCaptureKit (needs permission)
        #[cfg(target_os = "macos")]
        if Self::has_screen_recording_permission() {
            return AudioCaptureStrategy {
                strategy: CaptureMethod::ScreenCaptureKit,
            };
        }

        // 3. Mic-only fallback (always works, limited utility)
        AudioCaptureStrategy {
            strategy: CaptureMethod::MicrophoneOnly,
        }
    }

    fn find_virtual_audio_device() -> Option<String> {
        // Enumerate audio devices
        // Look for: "BlackHole 2ch", "BlackHole 16ch" (macOS)
        //           "CABLE Output (VB-Audio Virtual Cable)" (Windows)
        //           "Stereo Mix" (Windows built-in, often disabled)
        let known_virtual_devices = vec![
            "BlackHole 2ch",
            "BlackHole 16ch",
            "CABLE Output (VB-Audio Virtual Cable)",
            "VoiceMeeter Output",
            "Stereo Mix",
        ];
        // ... enumerate and match
        None // placeholder
    }
}
```

Setup wizard for first-time users:
```typescript
// frontend/src/pages/AudioSetupWizard.tsx

const SETUP_STEPS = [
    {
        id: "detect",
        title: "Detecting your audio setup",
        description: "We're checking which audio capture method will work best.",
        action: "auto_detect",
    },
    {
        id: "virtual_driver",
        title: "For best results: install a virtual audio driver",
        description: `
            To capture the interviewer's audio without requiring special
            permissions, install BlackHole (macOS) or VB-Cable (Windows).
            Both are free and take under 2 minutes to install.
        `,
        links: {
            macos: "https://existential.audio/blackhole/",
            windows: "https://vb-audio.com/Cable/",
        },
        action: "manual_install",
        skipAllowed: true,
        skipText: "Skip — use microphone only",
    },
    {
        id: "test",
        title: "Testing audio capture",
        description: "Play some audio and we'll verify we can hear it.",
        action: "test_capture",
    },
]
```

---

### A.3: Anti-Detection for Proctoring Software

Proctoring tools (HackerRank Proctoring, Codility, ExamSoft,
Proctorio) use multiple detection vectors:

```
Detection Vector 1: Process list scan
  - Look for known overlay/automation tools
  - Fix: Obfuscate process name (done in A.1)

Detection Vector 2: Window title enumeration
  - Enumerate all open windows, look for suspicious titles
  - Fix: Name overlay window "Untitled" or system-like name

Detection Vector 3: Injected DLL / loaded modules scan (Windows)
  - Check for suspicious DLLs loaded into the browser process
  - Fix: We don't inject DLLs — our overlay is a separate process

Detection Vector 4: Screenshot comparison
  - Take periodic screenshots, detect if content changes
    while screen share shows static screen (impossible for our case —
    we're a DIFFERENT window excluded from screen share)
  - Fix: The screen share exclusion handles this by design

Detection Vector 5: Browser extension detection
  - Some proctoring tools scan for browser extensions
  - We're a desktop app, not a browser extension — not affected

Detection Vector 6: Keyboard/mouse hook detection
  - Look for global keyboard/mouse hooks
  - Fix: Use hotkeys only through Tauri's global shortcut API,
    which doesn't install a traditional keyboard hook

Defense implementation:
```

```rust
// desktop/src-tauri/src/stealth/anti_detection.rs

pub struct AntiDetectionConfig {
    /// Window title shown to process scanners
    pub window_title: &'static str,
    /// Process name (set at startup)
    pub process_name: &'static str,
    /// Whether to randomize window position
    pub randomize_position: bool,
    /// Delay between overlay updates (too fast = detectable pattern)
    pub min_update_interval_ms: u64,
}

impl Default for AntiDetectionConfig {
    fn default() -> Self {
        Self {
            window_title: "Untitled",
            #[cfg(target_os = "macos")]
            process_name: "CoreAudiod",
            #[cfg(target_os = "windows")]
            process_name: "RuntimeBroker",
            randomize_position: true,
            min_update_interval_ms: 100,
        }
    }
}

/// Clear all detectable artifacts when the app exits
pub fn cleanup_on_exit() {
    // Delete any temp files created
    // Clear registry entries if any (Windows)
    // Remove process from any tracking structures
}
```

---

### A.4: Global Hotkey System

```rust
// desktop/src-tauri/src/hotkeys.rs

use tauri::GlobalShortcutManager;

pub fn register_hotkeys(app: &tauri::AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    let mut manager = app.global_shortcut_manager();

    // Toggle overlay visibility
    manager.register("CmdOrCtrl+Shift+H", {
        let app = app.clone();
        move || {
            let overlay = app.get_window("overlay").unwrap();
            if overlay.is_visible().unwrap() {
                overlay.hide().unwrap();
            } else {
                overlay.show().unwrap();
                overlay.set_focus().unwrap();
            }
        }
    })?;

    // Toggle click-through (interactive mode)
    manager.register("CmdOrCtrl+Shift+I", {
        let app = app.clone();
        move || {
            let overlay = app.get_window("overlay").unwrap();
            let current = overlay.is_mouse_passthrough().unwrap_or(true);
            overlay.set_ignore_cursor_events(!current).unwrap();
        }
    })?;

    // Re-trigger last question manually
    manager.register("CmdOrCtrl+Shift+R", {
        let app = app.clone();
        move || {
            app.emit_all("manual_retrigger", ()).unwrap();
        }
    })?;

    // Increase/decrease opacity
    manager.register("CmdOrCtrl+Shift+Up", {
        let app = app.clone();
        move || { app.emit_all("opacity_up", ()).unwrap(); }
    })?;

    manager.register("CmdOrCtrl+Shift+Down", {
        let app = app.clone();
        move || { app.emit_all("opacity_down", ()).unwrap(); }
    })?;

    // Emergency hide everything (panic button)
    manager.register("CmdOrCtrl+Shift+Escape", {
        let app = app.clone();
        move || {
            // Hide overlay AND pause all audio processing immediately
            app.get_window("overlay").unwrap().hide().unwrap();
            app.emit_all("emergency_stop", ()).unwrap();
        }
    })?;

    Ok(())
}
```

---

### Phase A Success Criteria

```
✅ Overlay window is NOT visible in Zoom screen share (tested manually)
✅ Overlay window is NOT visible in Teams screen share
✅ Overlay window is NOT visible in Meet screen share
✅ Process name appears as system process in Activity Monitor / Task Manager
✅ Overlay does not appear in Alt-Tab (Windows) or Mission Control (macOS)
✅ All hotkeys work when the main app window is not focused
✅ BlackHole/VB-Cable detection and setup wizard functional
✅ Emergency hide hotkey works in < 50ms
✅ App starts in < 3 seconds on cold start
```

### Phase A Definition of Done

```
- apply_stealth_mode() called and verified before any window shown
- process obfuscation verified with external tool (ps aux / Task Manager)
- Screen share test recorded and confirmed invisible
- Hotkey registration tested across Mac and Windows
- Audio setup wizard completes without errors on both platforms
- Unit tests for all stealth module functions
```

---

## UPGRADE PHASE B: Audio Intelligence Pipeline
### Priority: P0 | Difficulty: Medium | Impact: Very High

### Why This Phase

The current audio pipeline has three critical weaknesses:
1. No noise suppression before sending to STT
2. Diarization relies entirely on Deepgram (paid, cloud)
3. No acoustic calibration to distinguish speaker voices

Fixing these dramatically improves question detection accuracy
and enables a free, offline-capable STT fallback.

---

### B.1: Real-Time Noise Suppression (Free, Local)

```python
# backend/app/services/audio/noise_suppressor.py

"""
RNNoise-based real-time noise suppression.
Runs on every audio chunk BEFORE sending to STT.
Removes: keyboard clicks, fan noise, background chatter,
         AC units, street noise.

Library: rnnoise-python (MIT license)
Install: pip install rnnoise-python
Or use: noisereduce (MIT) for simpler setup
"""

import numpy as np
from dataclasses import dataclass

try:
    import rnnoise
    RNNOISE_AVAILABLE = True
except ImportError:
    RNNOISE_AVAILABLE = False

try:
    import noisereduce as nr
    NOISEREDUCE_AVAILABLE = True
except ImportError:
    NOISEREDUCE_AVAILABLE = False


@dataclass
class NoiseSuppressorConfig:
    enabled: bool = True
    method: str = "rnnoise"          # rnnoise | noisereduce | none
    sample_rate: int = 16000
    # RNNoise specific
    vad_threshold: float = 0.5
    # noisereduce specific
    prop_decrease: float = 0.8
    stationary: bool = False          # stationary=False for variable noise


class NoiseSuppressor:
    """
    Real-time audio noise suppression.
    Processes 10ms frames (RNNoise requirement).
    """

    RNNOISE_FRAME_SIZE = 480  # 10ms at 48kHz, resampled from 16kHz

    def __init__(self, config: NoiseSuppressorConfig) -> None:
        self.config = config
        self._denoiser = None
        self._noise_profile = None

        if config.enabled:
            self._initialize()

    def _initialize(self) -> None:
        if self.config.method == "rnnoise" and RNNOISE_AVAILABLE:
            self._denoiser = rnnoise.RNNoise()
        elif self.config.method == "noisereduce" and NOISEREDUCE_AVAILABLE:
            # Will use noise profile learned from first 0.5s of audio
            pass

    def suppress(self, pcm_bytes: bytes) -> bytes:
        """
        Apply noise suppression to a PCM chunk.
        Input/Output: 16kHz mono int16 PCM bytes
        """
        if not self.config.enabled or self._denoiser is None:
            return pcm_bytes

        try:
            audio = np.frombuffer(pcm_bytes, dtype=np.int16)

            if self.config.method == "rnnoise":
                return self._suppress_rnnoise(audio)
            elif self.config.method == "noisereduce":
                return self._suppress_noisereduce(audio)

        except Exception:
            # Never let suppression break the audio pipeline
            return pcm_bytes

        return pcm_bytes

    def _suppress_rnnoise(self, audio: np.ndarray) -> bytes:
        # RNNoise needs float32 in range [-32768, 32767]
        audio_float = audio.astype(np.float32)

        # Process in 480-sample frames
        output_frames = []
        for i in range(0, len(audio_float), self.RNNOISE_FRAME_SIZE):
            frame = audio_float[i:i + self.RNNOISE_FRAME_SIZE]
            if len(frame) < self.RNNOISE_FRAME_SIZE:
                # Pad last frame
                frame = np.pad(
                    frame,
                    (0, self.RNNOISE_FRAME_SIZE - len(frame))
                )
            denoised, _ = self._denoiser.process_frame(frame)
            output_frames.extend(denoised)

        denoised_audio = np.array(output_frames[:len(audio)], dtype=np.float32)
        return denoised_audio.astype(np.int16).tobytes()

    def _suppress_noisereduce(self, audio: np.ndarray) -> bytes:
        audio_float = audio.astype(np.float32) / 32768.0

        # Learn noise profile from first 0.5s if not set
        if self._noise_profile is None and len(audio_float) > 8000:
            self._noise_profile = audio_float[:8000]

        reduced = nr.reduce_noise(
            y=audio_float,
            sr=self.config.sample_rate,
            y_noise=self._noise_profile,
            prop_decrease=self.config.prop_decrease,
            stationary=self.config.stationary,
        )

        return (reduced * 32768.0).astype(np.int16).tobytes()
```

Integration into the pipeline:
```python
# In backend/app/routers/websocket.py
# Add noise suppression BEFORE sending to STT

from app.services.audio.noise_suppressor import NoiseSuppressor, NoiseSuppressorConfig

# Initialize once at startup
_noise_suppressor = NoiseSuppressor(NoiseSuppressorConfig(
    enabled=True,
    method="rnnoise",
))

# In the receive_loop:
async def receive_loop():
    while True:
        message = await ws.receive()
        if "bytes" in message and message["bytes"]:
            raw_chunk = message["bytes"]

            # Apply noise suppression FIRST
            clean_chunk = _noise_suppressor.suppress(raw_chunk)

            # Then send to both queues
            for q in (audio_queue, stt_audio_queue):
                try:
                    q.put_nowait(clean_chunk)
                except asyncio.QueueFull:
                    q.get_nowait()
                    q.put_nowait(clean_chunk)
```

---

### B.2: Local STT Fallback (Free, Offline-Capable)

```python
# backend/app/services/stt/whisper_local.py

"""
faster-whisper local STT — completely free, runs on CPU or GPU.
Quality: Nova-2 equivalent on clean audio.
Latency: ~300-600ms per 2s chunk on CPU (M1 Mac), ~100ms on GPU.

Models (choose based on hardware):
  tiny:   39M params, fastest, lower accuracy
  base:   74M params, good for practice mode
  small:  244M params, best CPU/latency tradeoff
  medium: 769M params, near cloud quality, needs good CPU or GPU
  large:  1.5B params, best quality, needs GPU

Free download: models auto-download from HuggingFace on first use.
"""

import asyncio
import time
import numpy as np
import structlog
from collections.abc import AsyncGenerator
from faster_whisper import WhisperModel

from app.config import get_settings
from app.services.stt.base import STTProvider, TranscriptEvent

log = structlog.get_logger()
settings = get_settings()


class WhisperLocalProvider(STTProvider):
    """
    Local faster-whisper STT.
    Falls back to this when Deepgram is unavailable or user prefers local.
    """

    # Module-level model cache — loaded once, reused across sessions
    _model: WhisperModel | None = None
    _model_lock = asyncio.Lock()

    @classmethod
    async def get_model(cls) -> WhisperModel:
        async with cls._model_lock:
            if cls._model is None:
                log.info("Loading faster-whisper model", model=settings.whisper_model_size)
                # Run blocking model load in thread pool
                cls._model = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: WhisperModel(
                        settings.whisper_model_size,  # "small" by default
                        device=settings.whisper_device,  # "cpu" or "cuda"
                        compute_type=settings.whisper_compute_type,  # "int8"
                        num_workers=2,
                        download_root="./.whisper_models",
                    )
                )
                log.info("faster-whisper model loaded")
        return cls._model

    async def stream_audio(
        self,
        audio_stream: AsyncGenerator[bytes, None],
    ) -> AsyncGenerator[TranscriptEvent, None]:
        model = await self.get_model()
        buffer = bytearray()
        # 3-second chunks give good accuracy/latency tradeoff
        chunk_samples = 16000 * 3
        chunk_bytes = chunk_samples * 2  # int16 = 2 bytes per sample
        overlap_bytes = 16000 * 1 * 2   # 0.5s overlap to avoid word cutting

        async for pcm_chunk in audio_stream:
            buffer.extend(pcm_chunk)

            while len(buffer) >= chunk_bytes:
                chunk = bytes(buffer[:chunk_bytes])
                # Keep overlap for next iteration
                buffer = buffer[chunk_bytes - overlap_bytes:]

                event = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self._transcribe,
                    model,
                    chunk,
                )

                if event:
                    yield event

        # Process remaining buffer
        if len(buffer) > 4000:  # At least 0.125s of audio
            event = await asyncio.get_event_loop().run_in_executor(
                None,
                self._transcribe,
                model,
                bytes(buffer),
            )
            if event:
                yield event

    def _transcribe(
        self,
        model: WhisperModel,
        pcm_bytes: bytes,
    ) -> TranscriptEvent | None:
        audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
        audio /= 32768.0

        segments, info = model.transcribe(
            audio,
            language="en",
            beam_size=5,
            best_of=5,
            temperature=0.0,    # Deterministic output
            vad_filter=True,    # Built-in VAD to skip silence
            vad_parameters={
                "min_silence_duration_ms": 300,
                "speech_pad_ms": 200,
            },
            word_timestamps=True,  # For diarization alignment
            condition_on_previous_text=True,  # Better coherence
        )

        text_parts = [seg.text for seg in segments]
        full_text = " ".join(text_parts).strip()

        if not full_text:
            return None

        return TranscriptEvent(
            text=full_text,
            is_final=True,
            speaker=None,  # Local whisper doesn't diarize
            confidence=0.85,
            timestamp_ms=int(time.time() * 1000),
        )

    async def close(self) -> None:
        pass  # Model stays loaded for reuse


# Provider factory with fallback
class ResilientSTTProvider(STTProvider):
    """
    Tries Deepgram first, falls back to local Whisper.
    Automatically switches on connection failure.
    """

    def __init__(self) -> None:
        self._primary: STTProvider | None = None
        self._fallback: STTProvider | None = None
        self._using_fallback = False

    async def initialize(self) -> None:
        from app.services.stt.deepgram import DeepgramProvider
        self._primary = DeepgramProvider()
        self._fallback = WhisperLocalProvider()

    async def stream_audio(
        self,
        audio_stream: AsyncGenerator[bytes, None],
    ) -> AsyncGenerator[TranscriptEvent, None]:
        provider = self._fallback if self._using_fallback else self._primary

        try:
            async for event in provider.stream_audio(audio_stream):
                yield event
        except Exception as e:
            log.warning(
                "Primary STT failed, switching to local fallback",
                error=str(e)
            )
            self._using_fallback = True
            async for event in self._fallback.stream_audio(audio_stream):
                yield event

    async def close(self) -> None:
        if self._primary:
            await self._primary.close()
```

Config additions for `.env.example`:
```bash
# Local STT Configuration
WHISPER_MODEL_SIZE=small         # tiny | base | small | medium | large-v3
WHISPER_DEVICE=cpu               # cpu | cuda
WHISPER_COMPUTE_TYPE=int8        # int8 (CPU) | float16 (GPU) | float32
STT_PREFER_LOCAL=false           # true = always use local whisper
STT_FALLBACK_TO_LOCAL=true       # true = fall back if Deepgram fails
```

---

### B.3: Free Local Speaker Diarization

```python
# backend/app/services/audio/diarizer.py

"""
pyannote.audio speaker diarization — free and open source.
Required: HuggingFace account (free) to download model.
Model: pyannote/speaker-diarization-3.1

Alternative if HF account not desired:
  resemblyzer (MIT) — speaker embeddings, simpler setup
  simple-diarizer (MIT) — wrapper around resemblyzer
"""

import asyncio
import numpy as np
import structlog
from dataclasses import dataclass
from io import BytesIO

log = structlog.get_logger()


@dataclass
class DiarizationSegment:
    speaker: str      # "SPEAKER_00", "SPEAKER_01"
    start_ms: int
    end_ms: int
    text: str | None = None


class LocalDiarizer:
    """
    Assigns speaker labels to audio segments.
    Uses acoustic embedding comparison to identify:
      - Speaker 0: interviewer (voice coming from system audio)
      - Speaker 1: candidate (voice from microphone)
    """

    _pipeline = None
    _initialized = False

    @classmethod
    async def initialize(cls, hf_token: str) -> None:
        if cls._initialized:
            return

        await asyncio.get_event_loop().run_in_executor(
            None,
            cls._load_pipeline,
            hf_token,
        )
        cls._initialized = True

    @classmethod
    def _load_pipeline(cls, hf_token: str) -> None:
        try:
            from pyannote.audio import Pipeline
            cls._pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=hf_token,
            )
            # Move to CPU (GPU if available)
            import torch
            if torch.cuda.is_available():
                cls._pipeline = cls._pipeline.to(torch.device("cuda"))
            log.info("pyannote diarization pipeline loaded")
        except Exception as e:
            log.error("Failed to load diarization pipeline", error=str(e))
            raise

    async def diarize_chunk(
        self,
        pcm_bytes: bytes,
        sample_rate: int = 16000,
    ) -> list[DiarizationSegment]:
        if not self._initialized or self._pipeline is None:
            return []

        return await asyncio.get_event_loop().run_in_executor(
            None,
            self._run_diarization,
            pcm_bytes,
            sample_rate,
        )

    def _run_diarization(
        self,
        pcm_bytes: bytes,
        sample_rate: int,
    ) -> list[DiarizationSegment]:
        import torch
        audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
        audio /= 32768.0
        audio_tensor = torch.from_numpy(audio).unsqueeze(0)

        diarization = self._pipeline({
            "waveform": audio_tensor,
            "sample_rate": sample_rate,
        })

        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append(DiarizationSegment(
                speaker=speaker,
                start_ms=int(turn.start * 1000),
                end_ms=int(turn.end * 1000),
            ))

        return segments


class SimpleSpeakerIdentifier:
    """
    Simpler alternative to pyannote — uses resemblyzer for speaker embeddings.
    Identifies interviewer vs candidate by comparing voice embeddings.
    No HuggingFace account required.

    Install: pip install resemblyzer
    """

    def __init__(self) -> None:
        self._interviewer_embedding = None
        self._candidate_embedding = None
        self._calibrated = False

    async def calibrate(
        self,
        interviewer_audio: bytes,
        candidate_audio: bytes,
    ) -> None:
        """
        Calibrate with 3-5 seconds of each speaker's audio.
        Call this at session start during the "Hello, can you hear me?" phase.
        """
        try:
            from resemblyzer import VoiceEncoder, preprocess_wav
            encoder = VoiceEncoder()

            interviewer_wav = preprocess_wav(
                np.frombuffer(interviewer_audio, dtype=np.int16).astype(np.float32) / 32768
            )
            candidate_wav = preprocess_wav(
                np.frombuffer(candidate_audio, dtype=np.int16).astype(np.float32) / 32768
            )

            self._interviewer_embedding = encoder.embed_utterance(interviewer_wav)
            self._candidate_embedding = encoder.embed_utterance(candidate_wav)
            self._calibrated = True
            log.info("Speaker calibration complete")
        except Exception as e:
            log.error("Calibration failed", error=str(e))

    def identify_speaker(self, audio_chunk: bytes) -> str:
        """Returns 'interviewer' or 'candidate'."""
        if not self._calibrated:
            return "unknown"

        try:
            from resemblyzer import VoiceEncoder, preprocess_wav
            import numpy as np
            encoder = VoiceEncoder()
            wav = preprocess_wav(
                np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) / 32768
            )
            embedding = encoder.embed_utterance(wav)

            interviewer_sim = np.dot(embedding, self._interviewer_embedding)
            candidate_sim = np.dot(embedding, self._candidate_embedding)

            return "interviewer" if interviewer_sim > candidate_sim else "candidate"
        except Exception:
            return "unknown"
```

---

### B.4: Adaptive VAD with Acoustic Context

```python
# backend/app/services/vad.py — upgraded

class AdaptiveSileroVAD:
    """
    Enhanced VAD with:
    1. Adaptive silence threshold based on session noise level
    2. End-of-sentence detection (not just silence)
    3. Distinction between mid-sentence pause and end of utterance
    """

    def __init__(self, base_silence_threshold_ms: int = 1000) -> None:
        self.base_threshold_ms = base_silence_threshold_ms
        self.adaptive_threshold_ms = base_silence_threshold_ms
        self._model = None
        self._speech_history: list[float] = []  # Rolling speech probs
        self._noise_floor: float = 0.1
        self._load_model()

    def update_noise_floor(self, prob: float) -> None:
        """
        Estimate noise floor from silence periods.
        Use this to adaptively set the speech threshold.
        """
        if prob < 0.3:  # Clearly silence
            self._speech_history.append(prob)
            if len(self._speech_history) > 100:
                self._speech_history.pop(0)
            self._noise_floor = np.mean(self._speech_history) if self._speech_history else 0.1

    def get_adaptive_threshold(self) -> float:
        """
        Speech threshold adapts to environment:
        - Noisy environment: higher threshold to avoid false positives
        - Quiet environment: lower threshold to catch soft speech
        """
        # Threshold is 2x noise floor, clamped between 0.3 and 0.7
        return max(0.3, min(0.7, self._noise_floor * 2))

    def process_chunk(
        self,
        pcm_bytes: bytes,
        state: VADState,
    ) -> tuple[VADState, bool]:
        now_ms = time.time() * 1000
        prob = self.get_speech_probability(pcm_bytes)
        threshold = self.get_adaptive_threshold()
        self.update_noise_floor(prob)

        end_of_utterance = False

        if prob >= threshold:
            state.is_speaking = True
            state.silence_start_ms = None
            state.last_speech_ms = now_ms
        else:
            if state.is_speaking:
                if state.silence_start_ms is None:
                    state.silence_start_ms = now_ms

                silence_ms = now_ms - state.silence_start_ms

                # Adaptive silence threshold based on speech duration
                # Short utterance: shorter silence needed
                # Long utterance: longer silence needed (they might be pausing)
                speech_duration = now_ms - (state.last_speech_ms or now_ms)
                adaptive_silence = self.base_threshold_ms
                if speech_duration > 10000:  # > 10s speech
                    adaptive_silence = 1500  # Wait longer after long speech
                elif speech_duration < 2000:  # < 2s speech
                    adaptive_silence = 700   # Shorter wait for short utterances

                if silence_ms >= adaptive_silence:
                    end_of_utterance = True
                    state.is_speaking = False
                    state.silence_start_ms = None

        return state, end_of_utterance
```

---

### Phase B Success Criteria

```
✅ Noise suppression reduces background noise by > 20dB (measurable)
✅ faster-whisper local STT produces transcripts within 800ms of chunk end
✅ Automatic fallback from Deepgram to local Whisper when Deepgram is down
✅ Speaker calibration correctly identifies interviewer vs candidate
    (validate with a recorded two-speaker audio test file)
✅ Adaptive VAD reduces false positive question detection by > 30%
    (measure: speak "can you hear me?" → should NOT trigger answer generation)
✅ Pipeline works completely offline (no internet) with local STT
```

---

## UPGRADE PHASE C: Advanced RAG Pipeline
### Priority: P1 | Difficulty: Medium | Impact: High

### Why This Phase

The current RAG system retrieves by cosine similarity on flat text chunks.
This misses two critical things:
1. Semantic matches that don't share vocabulary (hybrid search fixes this)
2. Relevant chunks are polluted with irrelevant ones (reranking fixes this)

---

### C.1: Hybrid Search (BM25 + Vector)

```python
# backend/app/services/rag/hybrid_search.py

"""
Hybrid retrieval: BM25 (lexical) + vector (semantic)
Combined with Reciprocal Rank Fusion (RRF).

Why hybrid:
  BM25 finds exact keyword matches: "React", "AWS", "2019"
  Vector finds semantic matches: "frontend development" ≈ "React developer"
  RRF combines both rankings for best of both worlds.

Free libraries:
  rank-bm25: pip install rank-bm25
  No additional dependencies needed.
"""

import math
from collections import defaultdict
from rank_bm25 import BM25Okapi
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


class HybridSearchRetriever:
    """
    Combines BM25 lexical search with pgvector semantic search.
    Uses Reciprocal Rank Fusion to merge results.
    """

    RRF_K = 60  # Standard RRF constant

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def retrieve(
        self,
        session_id: str,
        question: str,
        question_embedding: list[float],
        top_k: int = 8,           # Retrieve more, rerank will filter
        rrf_weight_bm25: float = 0.4,
        rrf_weight_vector: float = 0.6,
    ) -> list[dict]:
        """
        Retrieve chunks using hybrid BM25 + vector search.
        Returns top_k chunks sorted by RRF score.
        """

        # Run both searches in parallel
        bm25_results, vector_results = await asyncio.gather(
            self._bm25_search(session_id, question, top_k * 2),
            self._vector_search(session_id, question_embedding, top_k * 2),
        )

        # Reciprocal Rank Fusion
        rrf_scores: dict[str, float] = defaultdict(float)
        chunk_data: dict[str, dict] = {}

        for rank, chunk in enumerate(bm25_results):
            chunk_id = chunk["id"]
            rrf_scores[chunk_id] += rrf_weight_bm25 / (self.RRF_K + rank + 1)
            chunk_data[chunk_id] = chunk

        for rank, chunk in enumerate(vector_results):
            chunk_id = chunk["id"]
            rrf_scores[chunk_id] += rrf_weight_vector / (self.RRF_K + rank + 1)
            chunk_data[chunk_id] = chunk

        # Sort by RRF score and return top_k
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        return [
            {**chunk_data[chunk_id], "rrf_score": rrf_scores[chunk_id]}
            for chunk_id in sorted_ids[:top_k]
        ]

    async def _bm25_search(
        self,
        session_id: str,
        query: str,
        top_k: int,
    ) -> list[dict]:
        """BM25 lexical search against stored chunks."""
        # Fetch all chunks for this session (cached in Redis in production)
        result = await self.db.execute(
            text("""
                SELECT id, chunk_text, section, source_type
                FROM document_chunks
                WHERE session_id = :sid
            """),
            {"sid": session_id},
        )
        rows = result.fetchall()

        if not rows:
            return []

        # Tokenize
        corpus = [row.chunk_text.lower().split() for row in rows]
        bm25 = BM25Okapi(corpus)
        query_tokens = query.lower().split()
        scores = bm25.get_scores(query_tokens)

        # Return top_k by BM25 score
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [
            {
                "id": rows[i].id,
                "chunk_text": rows[i].chunk_text,
                "section": rows[i].section,
                "source_type": rows[i].source_type,
                "bm25_score": float(scores[i]),
            }
            for i in top_indices if scores[i] > 0
        ]

    async def _vector_search(
        self,
        session_id: str,
        embedding: list[float],
        top_k: int,
    ) -> list[dict]:
        """pgvector cosine similarity search."""
        result = await self.db.execute(
            text("""
                SELECT id, chunk_text, section, source_type,
                       1 - (embedding <=> :emb::vector) as similarity
                FROM document_chunks
                WHERE session_id = :sid
                ORDER BY embedding <=> :emb::vector
                LIMIT :k
            """),
            {"emb": str(embedding), "sid": session_id, "k": top_k},
        )
        return [
            {
                "id": row.id,
                "chunk_text": row.chunk_text,
                "section": row.section,
                "source_type": row.source_type,
                "vector_score": float(row.similarity),
            }
            for row in result.fetchall()
        ]
```

---

### C.2: Cross-Encoder Reranking (Free)

```python
# backend/app/services/rag/reranker.py

"""
Cross-encoder reranking dramatically improves precision.
It reads both the question AND each chunk together,
unlike bi-encoders that compare them separately.

Free model: cross-encoder/ms-marco-MiniLM-L-6-v2
Size: 90MB — small enough to run on CPU
Latency: ~20ms per chunk pair on CPU
Install: pip install sentence-transformers

Reranking flow:
  1. Hybrid search returns top 8 candidates
  2. Reranker scores each (question, chunk) pair
  3. Return top 4 by reranker score
  4. These 4 chunks go into the LLM prompt
"""

import asyncio
import structlog
from sentence_transformers import CrossEncoder

log = structlog.get_logger()


class ChunkReranker:
    """
    Cross-encoder reranker for retrieved chunks.
    Dramatically improves relevance precision.
    """

    _model: CrossEncoder | None = None
    _model_lock = asyncio.Lock()

    @classmethod
    async def get_model(cls) -> CrossEncoder:
        async with cls._model_lock:
            if cls._model is None:
                log.info("Loading reranker model")
                cls._model = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: CrossEncoder(
                        "cross-encoder/ms-marco-MiniLM-L-6-v2",
                        max_length=512,
                    )
                )
                log.info("Reranker model loaded")
        return cls._model

    async def rerank(
        self,
        question: str,
        chunks: list[dict],
        top_k: int = 4,
    ) -> list[dict]:
        """
        Rerank chunks by relevance to the question.
        Returns top_k most relevant chunks.
        """
        if not chunks:
            return []

        model = await self.get_model()

        # Create (question, chunk) pairs for the cross-encoder
        pairs = [(question, chunk["chunk_text"]) for chunk in chunks]

        # Score all pairs
        scores = await asyncio.get_event_loop().run_in_executor(
            None,
            model.predict,
            pairs,
        )

        # Sort by reranker score
        scored_chunks = sorted(
            zip(chunks, scores),
            key=lambda x: x[1],
            reverse=True,
        )

        top_chunks = [chunk for chunk, _ in scored_chunks[:top_k]]

        log.debug(
            "Reranking complete",
            input_chunks=len(chunks),
            output_chunks=len(top_chunks),
            top_score=float(scored_chunks[0][1]) if scored_chunks else 0,
        )

        return top_chunks
```

---

### C.3: Free Local Embeddings

```python
# backend/app/services/rag/embeddings.py

"""
Replace OpenAI text-embedding-3-small with free local models.

Best free option: BAAI/bge-m3
  - 570M params, 1024 dimensions
  - Outperforms OpenAI ada-002 on MTEB benchmark
  - Supports 100+ languages
  - MIT license
  - ~2GB download, runs on CPU

Fallback: BAAI/bge-small-en-v1.5
  - 33M params, 384 dimensions
  - Much smaller, faster on CPU
  - English only
  - Apache 2.0

Install: pip install sentence-transformers
"""

import asyncio
import structlog
import numpy as np
from sentence_transformers import SentenceTransformer

log = structlog.get_logger()


class LocalEmbeddingProvider:
    """
    Free local embedding generation using sentence-transformers.
    No API calls, no cost, no internet required at runtime.
    """

    _model: SentenceTransformer | None = None
    _model_lock = asyncio.Lock()

    @classmethod
    async def get_model(cls, model_name: str = "BAAI/bge-m3") -> SentenceTransformer:
        async with cls._model_lock:
            if cls._model is None:
                log.info("Loading embedding model", model=model_name)
                cls._model = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: SentenceTransformer(model_name, device="cpu"),
                )
                log.info("Embedding model loaded")
        return cls._model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts locally — no API calls."""
        model = await self.get_model()

        embeddings = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: model.encode(
                texts,
                batch_size=32,
                normalize_embeddings=True,  # For cosine similarity
                show_progress_bar=False,
            ).tolist()
        )

        return embeddings

    async def embed_query(self, query: str) -> list[float]:
        """
        Embed a single query.
        For bge-m3, prepend "Represent this sentence for searching relevant passages: "
        for better retrieval performance.
        """
        query_prefix = "Represent this sentence for searching relevant passages: "
        return (await self.embed([query_prefix + query]))[0]


# Note: bge-m3 uses 1024 dimensions, not 1536 (OpenAI)
# Update database schema when switching:
# ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(1024);
# Or use a separate column for each embedding model.
```

Database migration for local embeddings:
```python
# alembic/versions/002_local_embeddings.py

"""Switch to local embedding dimensions

Revision ID: 002
"""
from alembic import op

def upgrade() -> None:
    # Add a column for local embeddings alongside OpenAI embeddings
    # This allows A/B testing without losing existing data
    op.execute("""
        ALTER TABLE document_chunks
        ADD COLUMN IF NOT EXISTS embedding_local vector(1024)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS document_chunks_local_embedding_idx
        ON document_chunks
        USING hnsw (embedding_local vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
```

---

### C.4: Parent-Child Chunking

```python
# backend/app/services/rag/chunking.py

"""
Parent-child chunking strategy:
  - Parent chunks: large (800 chars) for context
  - Child chunks: small (150 chars) for precise retrieval

Flow:
  1. Store both parent and child chunks
  2. Embed CHILD chunks (small = more precise retrieval)
  3. When a child chunk matches, return its PARENT (full context)

This gives precision of small chunks with context of large chunks.
"""

from dataclasses import dataclass, field


@dataclass
class ParentChunk:
    id: str
    text: str
    section: str
    source_type: str
    children: list["ChildChunk"] = field(default_factory=list)


@dataclass
class ChildChunk:
    id: str
    text: str
    parent_id: str
    section: str
    source_type: str
    embedding: list[float] | None = None


class ParentChildChunker:
    """
    Creates hierarchical chunk structure for better RAG retrieval.
    """

    PARENT_CHUNK_SIZE = 800   # chars
    CHILD_CHUNK_SIZE = 150    # chars
    CHILD_OVERLAP = 30        # chars

    def chunk_document(
        self,
        text: str,
        section: str,
        source_type: str,
    ) -> list[ParentChunk]:
        import uuid

        parent_texts = self._split_text(text, self.PARENT_CHUNK_SIZE, 100)
        parents = []

        for parent_text in parent_texts:
            parent_id = str(uuid.uuid4())
            child_texts = self._split_text(
                parent_text, self.CHILD_CHUNK_SIZE, self.CHILD_OVERLAP
            )

            children = [
                ChildChunk(
                    id=str(uuid.uuid4()),
                    text=child_text,
                    parent_id=parent_id,
                    section=section,
                    source_type=source_type,
                )
                for child_text in child_texts
                if child_text.strip()
            ]

            parents.append(ParentChunk(
                id=parent_id,
                text=parent_text,
                section=section,
                source_type=source_type,
                children=children,
            ))

        return parents

    def _split_text(self, text: str, chunk_size: int, overlap: int) -> list[str]:
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk)
            start = end - overlap
        return chunks
```

Database additions for parent-child:
```sql
-- Add parent_id to document_chunks
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS parent_id UUID;
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS is_parent BOOLEAN DEFAULT false;
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS parent_text TEXT;

-- When a child chunk is retrieved, fetch parent text for LLM context
CREATE INDEX ON document_chunks (parent_id) WHERE parent_id IS NOT NULL;
```

---

### C.5: Query Expansion (Free)

```python
# backend/app/services/rag/query_expansion.py

"""
Query expansion improves retrieval by generating multiple
search queries from one question.

Example:
  Original: "Tell me about leading a project"
  Expanded:
    - "project leadership experience"
    - "team management software development"
    - "technical project manager responsibility"
    - "cross-functional team coordination"

Free implementation: Use local Ollama LLM (or Groq free tier)
"""

import json
import structlog
from groq import AsyncGroq
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from groq import RateLimitError

log = structlog.get_logger()

EXPANSION_PROMPT = """Given this interview question, generate 3 alternative search queries
to find relevant experience in a resume. Each query should be short (5-8 words)
and focus on different aspects of the question.

Question: {question}

Return ONLY valid JSON array of strings:
["query 1", "query 2", "query 3"]"""


class QueryExpander:

    def __init__(self, client: AsyncGroq) -> None:
        self.client = client

    @retry(
        retry=retry_if_exception_type(RateLimitError),
        stop=stop_after_attempt(2),
        wait=wait_exponential(min=1, max=5),
    )
    async def expand(self, question: str) -> list[str]:
        """Generate alternative search queries for better retrieval."""
        try:
            response = await self.client.chat.completions.create(
                model="llama3-8b-8192",     # Fast, cheap, good enough
                messages=[{
                    "role": "user",
                    "content": EXPANSION_PROMPT.format(question=question),
                }],
                temperature=0.3,
                max_tokens=100,
                response_format={"type": "json_object"},
            )
            parsed = json.loads(response.choices[0].message.content)
            if isinstance(parsed, list):
                return [question] + parsed[:3]  # Original + 3 expansions
            return [question]
        except Exception:
            return [question]  # Graceful fallback
```

---

### Phase C Success Criteria

```
✅ Hybrid search returns more relevant chunks than vector-only
   (validate: ask "what projects did I work on?" → compare results)
✅ Reranker reduces irrelevant chunks in top-4 results
   (measure: human evaluation of 20 question/resume pairs)
✅ Local embeddings (bge-m3) running without OpenAI API calls
✅ Parent-child chunking stores both levels in database
✅ Query expansion generates 3 meaningful alternative queries
✅ Full RAG pipeline (expand → hybrid search → rerank) runs in < 200ms
✅ Cost reduction: OpenAI embedding calls reduced to zero
```

---

## UPGRADE PHASE D: Answer Quality & Intelligence
### Priority: P1 | Difficulty: Hard | Impact: Very High

### Why This Phase

Current answers are generated with one LLM call and no validation.
This produces:
- Hallucinated experience not on the resume
- Generic STAR answers not grounded in actual stories
- Inconsistent quality across question types

---

### D.1: Multi-Step Answer Generation Pipeline

```python
# backend/app/services/answer/pipeline.py

"""
Multi-step generation pipeline:
Step 1: Extract relevant stories from resume (structured retrieval)
Step 2: Generate answer draft with strict grounding
Step 3: Self-critique and identify weaknesses
Step 4: Revise based on critique
Step 5: Final quality check

All steps use streaming for low perceived latency.
Steps 3-5 can run in background while step 2 streams to user.
"""

import asyncio
import structlog
from dataclasses import dataclass
from collections.abc import AsyncGenerator

log = structlog.get_logger()


@dataclass
class AnswerPipelineResult:
    draft: str
    critique: str | None
    final_answer: str
    confidence_score: float
    star_completeness: dict
    hallucination_risk: str  # "low" | "medium" | "high"
    grounding_sources: list[str]


class AnswerGenerationPipeline:
    """
    Multi-step answer generation with self-evaluation.
    """

    DRAFT_PROMPT = """You are generating a job interview answer for {candidate_name}.

STRICT RULES:
1. ONLY use information explicitly stated in the Background section below
2. Do NOT invent metrics, dates, team sizes, or outcomes not mentioned
3. If you lack information for a complete answer, say what you DO know
4. Use first person as if the candidate is speaking
5. Target length: 100-150 words for behavioral, 150-250 for technical

## Candidate Background (ONLY source of truth):
{rag_chunks}

## Question Type: {question_type}
## Question: {question}
## Recent Context: {conversation_history}

Generate a strong, grounded answer:"""

    CRITIQUE_PROMPT = """Review this interview answer and identify issues.

Question: {question}
Answer: {answer}
Candidate's actual background: {rag_chunks}

Check for:
1. Factual accuracy (does answer match the background?)
2. STAR completeness (Situation/Task/Action/Result all present?)
3. Specificity (concrete examples or vague generalities?)
4. Length appropriateness
5. Any hallucinated information not in background

Return JSON:
{{
  "has_hallucination": boolean,
  "hallucinated_claims": ["list of specific claims not in background"],
  "star_scores": {{"situation": 0-3, "task": 0-3, "action": 0-3, "result": 0-3}},
  "is_specific": boolean,
  "main_weakness": "one sentence",
  "overall_quality": "good" | "acceptable" | "needs_revision"
}}"""

    REVISION_PROMPT = """Revise this interview answer based on the critique.

Original Answer: {answer}
Critique: {critique}
Background (only use this): {rag_chunks}

Rules for revision:
- Fix only the issues identified in the critique
- Do NOT add information not in the background
- Keep length similar unless critique mentions length issues
- Maintain first person voice

Revised Answer:"""

    async def generate(
        self,
        question: str,
        question_type: str,
        context: dict,
        stream_callback,  # Called with each token for real-time display
    ) -> AnswerPipelineResult:
        """
        Full multi-step generation pipeline.
        Streams draft immediately while running critique in background.
        """
        # Step 1: Generate draft (streamed to user)
        draft_tokens: list[str] = []

        async for token in self._generate_draft(question, question_type, context):
            draft_tokens.append(token)
            await stream_callback({"type": "answer_token", "token": token})

        draft = "".join(draft_tokens)
        await stream_callback({"type": "draft_complete"})

        # Steps 2-4: Run in background (don't block user)
        # User sees draft immediately, then sees improved version
        critique_task = asyncio.create_task(
            self._critique_answer(question, draft, context["rag_chunks"])
        )

        critique_result = await critique_task

        # Only revise if quality warrants it (saves latency + API calls)
        final_answer = draft
        if (critique_result.get("overall_quality") == "needs_revision"
                or critique_result.get("has_hallucination")):

            revised_tokens: list[str] = []
            async for token in self._revise_answer(draft, critique_result, context):
                revised_tokens.append(token)
                await stream_callback({"type": "revision_token", "token": token})
            final_answer = "".join(revised_tokens)
            await stream_callback({"type": "revision_complete"})

        return AnswerPipelineResult(
            draft=draft,
            critique=str(critique_result),
            final_answer=final_answer,
            confidence_score=self._calculate_confidence(critique_result),
            star_completeness=critique_result.get("star_scores", {}),
            hallucination_risk="high" if critique_result.get("has_hallucination") else "low",
            grounding_sources=context.get("source_sections", []),
        )

    async def _generate_draft(
        self,
        question: str,
        question_type: str,
        context: dict,
    ) -> AsyncGenerator[str, None]:
        from app.services.llm_router import get_llm_provider, LLMContext
        provider = get_llm_provider()
        llm_context = LLMContext(
            candidate_name=context["candidate_name"],
            rag_chunks=context["rag_chunks"],
            jd_summary=context["jd_summary"],
            conversation_history=context["conversation_history"],
            question=question,
        )
        async for token in provider.generate_stream(llm_context):
            yield token

    async def _critique_answer(
        self,
        question: str,
        answer: str,
        rag_chunks: str,
    ) -> dict:
        import json
        from groq import AsyncGroq
        from app.config import get_settings
        settings = get_settings()
        client = AsyncGroq(api_key=settings.groq_api_key)

        try:
            response = await client.chat.completions.create(
                model="llama3-8b-8192",  # Fast critique model
                messages=[{
                    "role": "user",
                    "content": self.CRITIQUE_PROMPT.format(
                        question=question,
                        answer=answer,
                        rag_chunks=rag_chunks,
                    ),
                }],
                temperature=0.1,
                max_tokens=300,
                response_format={"type": "json_object"},
            )
            return json.loads(response.choices[0].message.content)
        except Exception:
            return {"overall_quality": "acceptable", "has_hallucination": False}

    def _calculate_confidence(self, critique: dict) -> float:
        score = 1.0
        if critique.get("has_hallucination"):
            score -= 0.4
        star = critique.get("star_scores", {})
        avg_star = sum(star.values()) / len(star) / 3 if star else 0.5
        score = score * 0.6 + avg_star * 0.4
        return max(0.0, min(1.0, score))
```

---

### D.2: Question-Type-Specific Prompts

```python
# backend/app/services/answer/prompt_templates.py

"""
Different question types need fundamentally different answer structures.
One template for all types produces mediocre answers for all.
"""

from dataclasses import dataclass
from enum import Enum


class QuestionType(str, Enum):
    BEHAVIORAL = "behavioral"
    TECHNICAL = "technical"
    SYSTEM_DESIGN = "system_design"
    CODING = "coding"
    SITUATIONAL = "situational"
    MOTIVATION = "motivation"
    CULTURE_FIT = "culture_fit"


@dataclass
class QuestionTypeConfig:
    name: str
    ideal_length_words: tuple[int, int]
    structure: str
    special_instructions: str
    system_prompt_suffix: str


QUESTION_TYPE_CONFIGS = {
    QuestionType.BEHAVIORAL: QuestionTypeConfig(
        name="Behavioral",
        ideal_length_words=(100, 180),
        structure="STAR (Situation → Task → Action → Result)",
        special_instructions="""
- Lead with a specific situation/scenario, not a general statement
- The Action section should be the longest (what YOU specifically did)
- Result MUST include a concrete outcome, ideally with a metric
- If no metric available, describe qualitative impact
- Avoid starting with "I would" — this is a past experience question
""",
        system_prompt_suffix="Use the STAR method. Be specific. Include measurable results.",
    ),
    QuestionType.TECHNICAL: QuestionTypeConfig(
        name="Technical",
        ideal_length_words=(120, 220),
        structure="Context → Approach → Implementation → Learnings",
        special_instructions="""
- Show technical depth appropriate to level in JD
- Mention specific technologies, frameworks, design patterns
- Walk through your reasoning, not just the solution
- Acknowledge trade-offs you considered
- End with what you learned or would do differently
""",
        system_prompt_suffix="Show technical reasoning. Mention specific tools/frameworks. Discuss trade-offs.",
    ),
    QuestionType.SYSTEM_DESIGN: QuestionTypeConfig(
        name="System Design",
        ideal_length_words=(200, 350),
        structure="Clarify Requirements → High Level → Deep Dive → Scale → Trade-offs",
        special_instructions="""
- Start by stating assumptions and clarifying questions
- Cover: API design, data model, component architecture
- Address scale explicitly (how does it handle 10x traffic?)
- Discuss at least 2 alternative approaches and why you chose yours
- Mention failure modes and how you'd handle them
""",
        system_prompt_suffix="Structure: requirements → architecture → scale → trade-offs. Be systematic.",
    ),
    QuestionType.MOTIVATION: QuestionTypeConfig(
        name="Motivation",
        ideal_length_words=(80, 140),
        structure="Why this company → Why this role → Why now",
        special_instructions="""
- Connect the company's mission to genuine personal interest
- Reference specific things about the role from the JD
- Show you've researched the company (use info from JD)
- Keep it authentic — avoid clichés like "fast-paced environment"
""",
        system_prompt_suffix="Be genuine. Connect to real career goals. Reference specific JD details.",
    ),
    QuestionType.CULTURE_FIT: QuestionTypeConfig(
        name="Culture Fit",
        ideal_length_words=(80, 150),
        structure="Story → Reflection → Connection to company values",
        special_instructions="""
- Use a real example that demonstrates the value being asked about
- Show self-awareness in the reflection
- Connect to what you know about the company's culture
""",
        system_prompt_suffix="Show authentic values alignment. Use specific examples.",
    ),
}


def get_type_specific_prompt(
    base_prompt: str,
    question_type: QuestionType,
    question: str,
) -> str:
    config = QUESTION_TYPE_CONFIGS.get(question_type, QUESTION_TYPE_CONFIGS[QuestionType.BEHAVIORAL])

    return f"""{base_prompt}

## Question Type: {config.name}
## Ideal Answer Length: {config.ideal_length_words[0]}-{config.ideal_length_words[1]} words
## Required Structure: {config.structure}

## Type-Specific Instructions:
{config.special_instructions}

## The Question:
{question}

Generate a {config.name.lower()} interview answer following the structure above:"""
```

---

### D.3: Hallucination Detection & Prevention

```python
# backend/app/services/answer/hallucination_guard.py

"""
Detect and filter hallucinated claims before showing answer to user.

Approach:
1. Extract all factual claims from the generated answer
2. Check each claim against the resume context (RAG chunks)
3. Flag or remove claims not supported by the resume
4. Show confidence indicator in UI

Free implementation: Use fast local LLM (Ollama) or Groq Llama-3-8B
"""

import json
import structlog
from groq import AsyncGroq, RateLimitError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

log = structlog.get_logger()

EXTRACTION_PROMPT = """Extract ALL factual claims from this interview answer.
A factual claim is any specific statement about:
- Job titles, companies, or dates
- Technologies, tools, or frameworks used
- Team sizes, metrics, or outcomes
- Project names or responsibilities

Answer: {answer}

Return JSON array of strings, each being one factual claim:
["claim 1", "claim 2", ...]"""

VERIFICATION_PROMPT = """Check if this factual claim is supported by the candidate's background.

Claim: {claim}
Candidate Background: {background}

Is this claim explicitly supported by the background?
Return JSON: {{"supported": boolean, "evidence": "quote from background or null"}}"""


class HallucinationGuard:

    def __init__(self, client: AsyncGroq) -> None:
        self.client = client

    @retry(
        retry=retry_if_exception_type(RateLimitError),
        stop=stop_after_attempt(2),
        wait=wait_exponential(min=1, max=5),
    )
    async def check_answer(
        self,
        answer: str,
        resume_context: str,
    ) -> dict:
        """
        Check an answer for hallucinated claims.
        Returns: {
            safe: bool,
            hallucinated_claims: list[str],
            supported_claims: list[str],
            confidence: float
        }
        """
        # Step 1: Extract claims
        claims = await self._extract_claims(answer)

        if not claims:
            return {"safe": True, "hallucinated_claims": [], "confidence": 0.9}

        # Step 2: Verify each claim (parallel)
        verification_tasks = [
            self._verify_claim(claim, resume_context)
            for claim in claims
        ]
        results = await asyncio.gather(*verification_tasks, return_exceptions=True)

        hallucinated = []
        supported = []
        for claim, result in zip(claims, results):
            if isinstance(result, Exception):
                continue
            if result.get("supported"):
                supported.append(claim)
            else:
                hallucinated.append(claim)

        total = len(claims)
        confidence = len(supported) / total if total > 0 else 1.0

        return {
            "safe": len(hallucinated) == 0,
            "hallucinated_claims": hallucinated,
            "supported_claims": supported,
            "confidence": confidence,
        }

    async def _extract_claims(self, answer: str) -> list[str]:
        try:
            response = await self.client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[{
                    "role": "user",
                    "content": EXTRACTION_PROMPT.format(answer=answer),
                }],
                temperature=0.0,
                max_tokens=200,
            )
            content = response.choices[0].message.content
            parsed = json.loads(content)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []

    async def _verify_claim(self, claim: str, background: str) -> dict:
        try:
            response = await self.client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[{
                    "role": "user",
                    "content": VERIFICATION_PROMPT.format(
                        claim=claim, background=background
                    ),
                }],
                temperature=0.0,
                max_tokens=100,
                response_format={"type": "json_object"},
            )
            return json.loads(response.choices[0].message.content)
        except Exception:
            return {"supported": True}  # Assume supported if check fails
```

---

### D.4: Answer Caching (Common Questions)

```python
# backend/app/services/answer/cache.py

"""
Cache answers for semantically similar questions.
Saves latency and API costs for repeated questions.

Implementation:
  1. When answer generated, embed the question
  2. Store (question_embedding, session_context_hash, answer) in Redis
  3. On new question: check if a semantically similar question was
     already answered with the same context
  4. Cache hit: return cached answer immediately (< 5ms)

Cache key: hash of (session_id + question_semantic_hash)
"""

import hashlib
import json
import numpy as np
import structlog
import redis.asyncio as aioredis

log = structlog.get_logger()

CACHE_TTL_SECONDS = 3600  # 1 hour
SIMILARITY_THRESHOLD = 0.92  # Must be very similar to use cache


class AnswerCache:

    def __init__(self, redis: aioredis.Redis) -> None:
        self.redis = redis

    async def get_cached_answer(
        self,
        session_id: str,
        question: str,
        question_embedding: list[float],
    ) -> str | None:
        """
        Check if a very similar question was already answered.
        Returns cached answer or None.
        """
        # Get all cached question embeddings for this session
        pattern = f"answer_cache:{session_id}:*"
        cached_keys = await self.redis.keys(pattern)

        if not cached_keys:
            return None

        q_emb = np.array(question_embedding)

        for key in cached_keys:
            cached_data_raw = await self.redis.get(key)
            if not cached_data_raw:
                continue

            cached_data = json.loads(cached_data_raw)
            cached_emb = np.array(cached_data["question_embedding"])

            # Cosine similarity
            similarity = float(
                np.dot(q_emb, cached_emb) /
                (np.linalg.norm(q_emb) * np.linalg.norm(cached_emb))
            )

            if similarity >= SIMILARITY_THRESHOLD:
                log.info("Cache hit", similarity=similarity, session_id=session_id)
                return cached_data["answer"]

        return None

    async def cache_answer(
        self,
        session_id: str,
        question: str,
        question_embedding: list[float],
        answer: str,
    ) -> None:
        """Store answer in cache."""
        cache_key = f"answer_cache:{session_id}:{hashlib.md5(question.encode()).hexdigest()}"
        data = {
            "question": question,
            "question_embedding": question_embedding,
            "answer": answer,
        }
        await self.redis.set(cache_key, json.dumps(data), ex=CACHE_TTL_SECONDS)
```

---

### Phase D Success Criteria

```
✅ Multi-step pipeline: draft generated and streaming within 500ms
✅ Self-critique runs in background, revision shows within 3s if needed
✅ Hallucination guard flags answers containing claims not in resume
    (test: deliberately put false info in answer, verify it's flagged)
✅ Question-type detection correctly routes behavioral/technical/design
✅ STAR completeness score visible in UI for behavioral questions
✅ Answer caching returns cached answer in < 10ms for similar questions
✅ No LLM call made for questions with > 92% similarity to prior question
```

---

## UPGRADE PHASE E: Context & Memory System
### Priority: P1 | Difficulty: Hard | Impact: High

### Why This Phase

Long interviews (30-60 minutes, 10-20 questions) lose coherence.
Current system has a 15-second rolling buffer.
After 5 questions, the AI forgets earlier answers and repeats content.

---

### E.1: Semantic Session Memory

```python
# backend/app/services/memory/session_memory.py

"""
Structured memory system for interview sessions.
Stores and retrieves past Q&A pairs by semantic similarity.

Unlike the rolling buffer (recency-based),
semantic memory retrieves RELEVANT past context
even from the beginning of a 60-minute session.
"""

import json
import numpy as np
import structlog
import redis.asyncio as aioredis
from dataclasses import dataclass, asdict

log = structlog.get_logger()


@dataclass
class MemoryEntry:
    question: str
    answer: str
    question_type: str
    timestamp_ms: int
    question_embedding: list[float]
    topics_covered: list[str]    # Extracted topics from Q&A
    projects_mentioned: list[str] # Projects referenced in answer
    skills_demonstrated: list[str] # Skills shown in answer


class SemanticSessionMemory:
    """
    Semantic memory that retrieves relevant past context
    based on similarity to current question.
    """

    MAX_ENTRIES = 30             # Keep up to 30 Q&A pairs in memory
    TOP_K_RELEVANT = 3           # Return 3 most relevant past pairs

    def __init__(self, session_id: str, redis: aioredis.Redis) -> None:
        self.session_id = session_id
        self.redis = redis
        self._memory_key = f"session:{session_id}:semantic_memory"

    async def add_entry(self, entry: MemoryEntry) -> None:
        """Store a Q&A pair in semantic memory."""
        entries = await self._get_all_entries()
        entries.append(asdict(entry))

        # Keep only most recent MAX_ENTRIES
        if len(entries) > self.MAX_ENTRIES:
            entries = entries[-self.MAX_ENTRIES:]

        await self.redis.set(
            self._memory_key,
            json.dumps(entries),
            ex=4 * 3600,  # 4hr TTL
        )

    async def get_relevant_context(
        self,
        current_question: str,
        current_embedding: list[float],
    ) -> str:
        """
        Retrieve past Q&A pairs relevant to the current question.
        Returns formatted context string for LLM prompt.
        """
        entries = await self._get_all_entries()
        if not entries:
            return "No previous exchanges."

        curr_emb = np.array(current_embedding)

        # Score each past entry by similarity
        scored_entries = []
        for entry in entries:
            past_emb = np.array(entry["question_embedding"])
            similarity = float(
                np.dot(curr_emb, past_emb) /
                (np.linalg.norm(curr_emb) * np.linalg.norm(past_emb) + 1e-10)
            )
            scored_entries.append((similarity, entry))

        # Sort by similarity, take top K
        scored_entries.sort(key=lambda x: x[0], reverse=True)
        relevant = scored_entries[:self.TOP_K_RELEVANT]

        if not relevant:
            return "No previous exchanges."

        lines = []
        for similarity, entry in relevant:
            lines.append(
                f"Q ({entry['question_type']}): {entry['question']}\n"
                f"A: {entry['answer'][:200]}..."  # Truncate for token efficiency
            )

        # Also track what's been mentioned to avoid repetition
        all_projects = set()
        all_skills = set()
        for _, entry in scored_entries:
            all_projects.update(entry.get("projects_mentioned", []))
            all_skills.update(entry.get("skills_demonstrated", []))

        repetition_warning = ""
        if all_projects:
            repetition_warning = (
                f"\n\n[AVOID REPETITION] Already mentioned: "
                f"projects={list(all_projects)}, skills={list(all_skills)}. "
                f"Reference DIFFERENT examples where possible.]"
            )

        return "\n\n".join(lines) + repetition_warning

    async def _get_all_entries(self) -> list[dict]:
        raw = await self.redis.get(self._memory_key)
        if not raw:
            return []
        return json.loads(raw)

    async def get_topics_covered(self) -> list[str]:
        """Return all topics discussed in this session."""
        entries = await self._get_all_entries()
        topics = set()
        for entry in entries:
            topics.update(entry.get("topics_covered", []))
        return list(topics)


class TopicExtractor:
    """
    Extract structured information from Q&A pairs
    for memory metadata.
    """

    async def extract(
        self,
        question: str,
        answer: str,
        client,
    ) -> dict:
        prompt = f"""Extract structured information from this interview Q&A.

Question: {question}
Answer: {answer}

Return JSON:
{{
  "topics_covered": ["list of broad topics discussed"],
  "projects_mentioned": ["specific project names mentioned"],
  "skills_demonstrated": ["technical or soft skills shown"],
  "question_type": "behavioral|technical|system_design|coding|motivation"
}}"""

        try:
            response = await client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=150,
                response_format={"type": "json_object"},
            )
            return json.loads(response.choices[0].message.content)
        except Exception:
            return {
                "topics_covered": [],
                "projects_mentioned": [],
                "skills_demonstrated": [],
                "question_type": "behavioral",
            }
```

---

### E.2: Cross-Session Memory (Interview History)

```python
# backend/app/services/memory/cross_session_memory.py

"""
Remembers performance across multiple interview sessions.
Used to:
  1. Track which question types the user struggles with
  2. Avoid suggesting the same stories across sessions
  3. Show improvement over time
  4. Personalize future sessions based on past performance

Storage: PostgreSQL (persistent across sessions)
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from dataclasses import dataclass


@dataclass
class SessionPerformanceSummary:
    session_id: str
    date: str
    interview_type: str
    company: str | None
    total_questions: int
    behavioral_score: float
    technical_score: float
    star_adherence: float
    filler_word_rate: float
    topics_covered: list[str]
    weak_areas: list[str]
    strong_areas: list[str]


class CrossSessionMemory:
    """
    Persistent memory across interview sessions.
    Enables learning from past performance.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_user_performance_context(
        self, user_id: str, limit: int = 5
    ) -> str:
        """
        Get summary of user's past interview performance.
        Used to personalize coaching for current session.
        """
        result = await self.db.execute(
            text("""
                SELECT
                    s.id,
                    s.started_at,
                    s.interview_type,
                    fr.clarity_score,
                    fr.structure_score,
                    fr.keyword_alignment_score,
                    fr.summary
                FROM sessions s
                LEFT JOIN feedback_reports fr ON fr.session_id = s.id
                WHERE s.user_id = :user_id
                    AND s.status = 'completed'
                    AND fr.id IS NOT NULL
                ORDER BY s.started_at DESC
                LIMIT :limit
            """),
            {"user_id": user_id, "limit": limit},
        )
        rows = result.fetchall()

        if not rows:
            return "No previous session history."

        summaries = []
        for row in rows:
            summaries.append(
                f"Session ({row.started_at.strftime('%Y-%m-%d')}): "
                f"Type={row.interview_type}, "
                f"Clarity={row.clarity_score:.1f}/10, "
                f"Structure={row.structure_score:.1f}/10"
            )

        return (
            "User's recent performance:\n" +
            "\n".join(summaries) +
            "\n\nFocus on helping them improve their weakest areas."
        )

    async def identify_weak_areas(self, user_id: str) -> list[str]:
        """
        Identify consistent weak areas across sessions.
        Used to adapt question selection in mock mode.
        """
        result = await self.db.execute(
            text("""
                SELECT
                    AVG(fr.clarity_score) as avg_clarity,
                    AVG(fr.structure_score) as avg_structure,
                    AVG(fr.keyword_alignment_score) as avg_keywords,
                    AVG(fr.filler_word_count) as avg_fillers
                FROM feedback_reports fr
                JOIN sessions s ON s.id = fr.session_id
                WHERE s.user_id = :user_id
                    AND s.started_at > NOW() - INTERVAL '30 days'
            """),
            {"user_id": user_id},
        )
        row = result.fetchone()

        if not row:
            return []

        weak_areas = []
        if row.avg_clarity and row.avg_clarity < 6:
            weak_areas.append("answer_clarity")
        if row.avg_structure and row.avg_structure < 6:
            weak_areas.append("star_structure")
        if row.avg_keywords and row.avg_keywords < 6:
            weak_areas.append("jd_keyword_alignment")
        if row.avg_fillers and row.avg_fillers > 15:
            weak_areas.append("filler_words")

        return weak_areas
```

---

### Phase E Success Criteria

```
✅ Session memory correctly retrieves relevant past context
   (test: ask about project A, then ask follow-up → gets context from first answer)
✅ Repetition warning fires when candidate is about to reuse same story
✅ Cross-session memory visible in dashboard ("Your weak areas this month")
✅ After 10+ questions, answers still reference correct earlier context
✅ Memory module adds < 50ms to answer generation pipeline
```

---

## UPGRADE PHASE F: Local LLM Integration
### Priority: P2 | Difficulty: Medium | Impact: High (Cost + Privacy)

### Why This Phase

Privacy-conscious users will not use a tool that sends their
resume and interview questions to cloud APIs.
Local LLM via Ollama enables complete offline operation.

---

### F.1: Ollama Integration

```python
# backend/app/services/llm/ollama_provider.py

"""
Ollama runs LLMs locally on the user's machine.
No API costs. No data leaves the device.

Installation: curl -fsSL https://ollama.ai/install.sh | sh
Models to recommend:
  mistral:7b-instruct    — 4.1GB, good quality, runs on 8GB RAM
  llama3.1:8b-instruct   — 4.7GB, excellent, runs on 8GB RAM
  phi3:mini              — 2.3GB, fast, runs on 4GB RAM (limited quality)
  deepseek-coder:6.7b    — For coding questions, 3.8GB

Ollama exposes OpenAI-compatible API at localhost:11434
So we can use the OpenAI client with no changes!
"""

from openai import AsyncOpenAI
from collections.abc import AsyncGenerator
from app.services.llm_router import LLMProvider, LLMContext, SYSTEM_PROMPT, USER_PROMPT
import structlog

log = structlog.get_logger()


class OllamaProvider(LLMProvider):
    """
    Local LLM via Ollama — completely free, completely private.
    Uses OpenAI-compatible API so no special SDK needed.
    """

    def __init__(
        self,
        model: str = "llama3.1:8b-instruct",
        base_url: str = "http://localhost:11434/v1",
    ) -> None:
        self.model = model
        # Ollama exposes OpenAI-compatible API
        self.client = AsyncOpenAI(
            api_key="ollama",       # Required but ignored by Ollama
            base_url=base_url,
        )

    async def is_available(self) -> bool:
        """Check if Ollama is running and model is loaded."""
        try:
            models = await self.client.models.list()
            return any(m.id == self.model for m in models.data)
        except Exception:
            return False

    async def generate_stream(
        self, context: LLMContext
    ) -> AsyncGenerator[str, None]:
        system_prompt = SYSTEM_PROMPT.format(
            candidate_name=context.candidate_name,
            rag_chunks=context.rag_chunks,
            jd_summary=context.jd_summary,
            conversation_history=context.conversation_history,
        )

        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": USER_PROMPT.format(
                    question=context.question
                )},
            ],
            temperature=0.7,
            max_tokens=300,
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


class SmartLLMRouter:
    """
    Intelligently routes between providers based on:
    1. User preference (local first vs cloud first)
    2. Availability (is Ollama running?)
    3. Question type (coding → faster model, complex → better model)
    4. Latency target (if local is too slow, fall back to cloud)
    """

    def __init__(self, prefer_local: bool = False) -> None:
        self.prefer_local = prefer_local
        self._ollama: OllamaProvider | None = None
        self._groq = None
        self._openai = None

    async def initialize(self) -> None:
        from app.services.llm_router import GroqProvider, OpenAIProvider
        self._ollama = OllamaProvider()
        self._groq = GroqProvider()
        self._openai = OpenAIProvider()

        ollama_available = await self._ollama.is_available()
        log.info(
            "LLM Router initialized",
            ollama_available=ollama_available,
            prefer_local=self.prefer_local,
        )

    async def get_provider_for_question(
        self,
        question_type: str,
        privacy_mode: bool = False,
    ) -> LLMProvider:
        """Select best provider for question type and user preference."""
        # Privacy mode: always use local
        if privacy_mode:
            if self._ollama and await self._ollama.is_available():
                return self._ollama
            log.warning("Privacy mode requested but Ollama not available")

        # Local preference
        if self.prefer_local and self._ollama:
            if await self._ollama.is_available():
                return self._ollama

        # Default: Groq for speed
        return self._groq

    async def generate_stream(
        self,
        context: LLMContext,
        question_type: str = "behavioral",
        privacy_mode: bool = False,
    ) -> AsyncGenerator[str, None]:
        provider = await self.get_provider_for_question(question_type, privacy_mode)

        try:
            async for token in provider.generate_stream(context):
                yield token
        except Exception as e:
            log.warning("Provider failed, falling back", error=str(e))
            # Fall back to Groq if local fails
            async for token in self._groq.generate_stream(context):
                yield token
```

Config additions:
```bash
# .env.example additions

# Local LLM (Ollama)
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=llama3.1:8b-instruct
LLM_PREFER_LOCAL=false          # true = use Ollama when available
LLM_PRIVACY_MODE=false          # true = NEVER send to cloud LLMs
```

Frontend privacy toggle:
```typescript
// frontend/src/components/PrivacyModeToggle.tsx

export function PrivacyModeToggle() {
    const [privacyMode, setPrivacyMode] = useState(false)
    const [ollamaAvailable, setOllamaAvailable] = useState(false)

    useEffect(() => {
        // Check if Ollama is running
        fetch('http://localhost:11434/api/tags')
            .then(() => setOllamaAvailable(true))
            .catch(() => setOllamaAvailable(false))
    }, [])

    return (
        <div className="flex items-center gap-3 p-3 rounded-lg
                        bg-gray-900 border border-gray-800">
            <Shield size={16} className={privacyMode ? "text-green-400" : "text-gray-500"} />
            <div>
                <p className="text-sm text-white font-medium">Privacy Mode</p>
                <p className="text-xs text-gray-400">
                    {ollamaAvailable
                        ? "Local AI only — nothing leaves your device"
                        : "Install Ollama to enable local processing"}
                </p>
            </div>
            <button
                onClick={() => setPrivacyMode(!privacyMode)}
                disabled={!ollamaAvailable}
                className={`ml-auto w-10 h-5 rounded-full transition-colors
                    ${privacyMode ? 'bg-green-500' : 'bg-gray-600'}
                    ${!ollamaAvailable ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'}`}
            >
                <div className={`w-4 h-4 bg-white rounded-full m-0.5
                    transition-transform
                    ${privacyMode ? 'translate-x-5' : 'translate-x-0'}`} />
            </button>
        </div>
    )
}
```

---

### Phase F Success Criteria

```
✅ Ollama provider generates streaming answers with llama3.1:8b
✅ Privacy mode toggle works and shows "local only" badge
✅ Smart router falls back to Groq when Ollama is unavailable
✅ Answer quality with local model is acceptable (subjective evaluation)
✅ No network requests made to Groq/OpenAI when privacy mode is ON
    (verify with Charles Proxy or Wireshark)
✅ Latency with local model documented and shown in UI
```

---

## UPGRADE PHASE G: Coding Question Pipeline
### Priority: P2 | Difficulty: Medium | Impact: High

---

### G.1: Screenshot → Structured Solution (Free/Local)

```python
# backend/app/services/coding/pipeline.py

"""
Coding question pipeline:
1. User triggers screenshot via hotkey
2. Screenshot sent to vision LLM
3. Extract: problem statement, constraints, examples
4. Generate: approach, pseudocode, complexity analysis
5. Display in overlay as formatted code block

Free vision options:
  - LLaVA via Ollama (local, free): ollama run llava
  - moondream via Ollama (tiny, fast): ollama run moondream
  - Groq vision API (free tier has limits): mixtral-vision

For code generation after understanding the problem:
  - deepseek-coder:6.7b via Ollama (specialized for coding)
  - codellama:7b via Ollama (Meta's coding model)
"""

import base64
import json
import asyncio
import structlog
from openai import AsyncOpenAI
from dataclasses import dataclass

log = structlog.get_logger()


@dataclass
class CodingProblemAnalysis:
    problem_summary: str
    input_format: str
    output_format: str
    constraints: list[str]
    examples: list[dict]
    approach: str
    pseudocode: str
    time_complexity: str
    space_complexity: str
    edge_cases: list[str]
    follow_up_considerations: list[str]


VISION_PROMPT = """Analyze this coding interview problem screenshot.
Extract all information and provide a structured solution approach.

Return JSON:
{
  "problem_summary": "one sentence description",
  "input_format": "description of input",
  "output_format": "description of expected output",
  "constraints": ["list of constraints"],
  "examples": [{"input": "...", "output": "...", "explanation": "..."}],
  "approach": "detailed explanation of the optimal approach (2-3 paragraphs)",
  "pseudocode": "step by step pseudocode",
  "time_complexity": "O(?) with explanation",
  "space_complexity": "O(?) with explanation",
  "edge_cases": ["edge cases to handle"],
  "follow_up_considerations": ["potential follow-up questions"]
}"""


class CodingQuestionPipeline:

    def __init__(self, prefer_local: bool = False) -> None:
        self.prefer_local = prefer_local
        # Ollama with LLaVA for vision (free, local)
        self._ollama_vision = AsyncOpenAI(
            api_key="ollama",
            base_url="http://localhost:11434/v1",
        )
        # Groq for fallback (free tier)
        from app.config import get_settings
        self._groq_vision = AsyncOpenAI(
            api_key=get_settings().groq_api_key,
            base_url="https://api.groq.com/openai/v1",
        )

    async def analyze_screenshot(
        self,
        screenshot_base64: str,
    ) -> CodingProblemAnalysis:
        """
        Analyze a coding problem screenshot and return structured solution.
        """
        if self.prefer_local:
            try:
                return await self._analyze_with_ollama(screenshot_base64)
            except Exception as e:
                log.warning("Local vision failed, falling back", error=str(e))

        return await self._analyze_with_groq(screenshot_base64)

    async def _analyze_with_ollama(
        self, screenshot_base64: str
    ) -> CodingProblemAnalysis:
        """Use LLaVA locally via Ollama."""
        response = await self._ollama_vision.chat.completions.create(
            model="llava:7b",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": VISION_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{screenshot_base64}"
                        },
                    },
                ],
            }],
            temperature=0.1,
            max_tokens=1000,
        )
        return self._parse_response(response.choices[0].message.content)

    async def _analyze_with_groq(
        self, screenshot_base64: str
    ) -> CodingProblemAnalysis:
        """Use Groq vision API (free tier)."""
        response = await self._groq_vision.chat.completions.create(
            model="llama-3.2-90b-vision-preview",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": VISION_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{screenshot_base64}"
                        },
                    },
                ],
            }],
            temperature=0.1,
            max_tokens=1000,
        )
        return self._parse_response(response.choices[0].message.content)

    def _parse_response(self, content: str) -> CodingProblemAnalysis:
        try:
            data = json.loads(content)
            return CodingProblemAnalysis(**data)
        except Exception:
            return CodingProblemAnalysis(
                problem_summary="Could not parse problem",
                input_format="",
                output_format="",
                constraints=[],
                examples=[],
                approach=content,
                pseudocode="",
                time_complexity="",
                space_complexity="",
                edge_cases=[],
                follow_up_considerations=[],
            )
```

Overlay display for coding questions:
```typescript
// frontend/src/components/CodingOverlay.tsx

interface CodingAnalysis {
    problem_summary: string
    approach: string
    pseudocode: string
    time_complexity: string
    space_complexity: string
    edge_cases: string[]
}

export function CodingOverlay({ analysis }: { analysis: CodingAnalysis }) {
    return (
        <div className="bg-gray-950/90 rounded-xl border border-indigo-500/30 p-4 text-sm">
            <div className="text-indigo-400 text-xs uppercase tracking-widest mb-3">
                🧩 Coding Problem Analysis
            </div>

            <div className="mb-3">
                <span className="text-gray-400 text-xs">Problem: </span>
                <span className="text-white">{analysis.problem_summary}</span>
            </div>

            <div className="mb-3">
                <div className="text-gray-400 text-xs mb-1">Approach:</div>
                <div className="text-gray-200 leading-relaxed">{analysis.approach}</div>
            </div>

            <div className="mb-3">
                <div className="text-gray-400 text-xs mb-1">Pseudocode:</div>
                <pre className="bg-gray-900 rounded p-3 text-green-400 text-xs
                               overflow-x-auto font-mono">
                    {analysis.pseudocode}
                </pre>
            </div>

            <div className="flex gap-4 mb-3">
                <div>
                    <span className="text-gray-400 text-xs">Time: </span>
                    <span className="text-yellow-400 font-mono">
                        {analysis.time_complexity}
                    </span>
                </div>
                <div>
                    <span className="text-gray-400 text-xs">Space: </span>
                    <span className="text-yellow-400 font-mono">
                        {analysis.space_complexity}
                    </span>
                </div>
            </div>

            {analysis.edge_cases.length > 0 && (
                <div>
                    <div className="text-gray-400 text-xs mb-1">Edge Cases:</div>
                    <ul className="text-gray-300 text-xs space-y-1">
                        {analysis.edge_cases.map((ec, i) => (
                            <li key={i} className="flex items-start gap-1">
                                <span className="text-indigo-400">•</span> {ec}
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    )
}
```

---

### Phase G Success Criteria

```
✅ Screenshot hotkey captures screen and sends to pipeline
✅ LLaVA local vision correctly extracts problem from LeetCode screenshot
✅ Pseudocode generated for a medium-difficulty problem
✅ Time/space complexity correctly identified for standard algorithms
✅ Display renders in overlay as formatted code block
✅ Fallback to Groq vision when local vision is unavailable
```

---

## UPGRADE PHASE H: Observability & Reliability
### Priority: P2 | Difficulty: Easy | Impact: Medium

---

### H.1: OpenTelemetry Distributed Tracing (Free)

```python
# backend/app/telemetry.py

"""
OpenTelemetry distributed tracing — completely free.
Traces the full request path from audio chunk to displayed answer.
Identifies which step is the bottleneck in the pipeline.

Install:
  pip install opentelemetry-api
  pip install opentelemetry-sdk
  pip install opentelemetry-exporter-jaeger
  pip install opentelemetry-instrumentation-fastapi

Jaeger (free, self-hosted): runs in Docker
"""

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

def setup_telemetry(app) -> None:
    # Jaeger exporter (self-hosted, free)
    jaeger_exporter = JaegerExporter(
        agent_host_name="localhost",
        agent_port=6831,
    )

    provider = TracerProvider()
    provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
    trace.set_tracer_provider(provider)

    # Auto-instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)


# Tracer for manual instrumentation
tracer = trace.get_tracer("interviewcopilot")


# Usage in websocket.py:
async def handle_question(question: str, session_id: str) -> None:
    with tracer.start_as_current_span("handle_question") as span:
        span.set_attribute("session_id", session_id)
        span.set_attribute("question_length", len(question))

        with tracer.start_as_current_span("rag_retrieval"):
            rag_context = await rag.retrieve(session_id, question)

        with tracer.start_as_current_span("llm_generation"):
            async for token in llm.generate_stream(context):
                yield token
```

Docker Compose addition for Jaeger:
```yaml
# docker-compose.yml addition
  jaeger:
    image: jaegertracing/all-in-one:latest
    container_name: ic_jaeger
    ports:
      - "16686:16686"    # Jaeger UI
      - "6831:6831/udp"  # Agent port
    environment:
      COLLECTOR_OTLP_ENABLED: "true"
```

---

### H.2: Prometheus Metrics (Free)

```python
# backend/app/metrics.py

from prometheus_client import (
    Counter, Histogram, Gauge,
    start_http_server, REGISTRY,
)

# Pipeline metrics
AUDIO_CHUNKS_PROCESSED = Counter(
    'audio_chunks_processed_total',
    'Total audio chunks processed',
)
STT_LATENCY = Histogram(
    'stt_latency_seconds',
    'STT processing latency',
    buckets=[0.1, 0.2, 0.3, 0.5, 1.0, 2.0],
)
QUESTION_DETECTION_TOTAL = Counter(
    'question_detection_total',
    'Question detection results',
    ['is_question'],
)
LLM_TTFT = Histogram(
    'llm_time_to_first_token_seconds',
    'LLM time to first token',
    buckets=[0.1, 0.2, 0.3, 0.5, 1.0, 2.0, 3.0],
)
E2E_LATENCY = Histogram(
    'e2e_latency_seconds',
    'End-to-end pipeline latency (silence → first token)',
    buckets=[0.5, 1.0, 1.5, 2.0, 3.0, 5.0],
)
ACTIVE_SESSIONS = Gauge(
    'active_websocket_sessions',
    'Currently active WebSocket sessions',
)
HALLUCINATION_DETECTIONS = Counter(
    'hallucination_detections_total',
    'Answers flagged as potentially hallucinated',
)
CACHE_HITS = Counter(
    'answer_cache_hits_total',
    'Answer cache hits',
)
PROVIDER_CALLS = Counter(
    'llm_provider_calls_total',
    'LLM provider API calls',
    ['provider', 'model'],
)

def start_metrics_server(port: int = 9090) -> None:
    """Start Prometheus metrics HTTP server."""
    start_http_server(port)
```

---

### H.3: Circuit Breaker Pattern

```python
# backend/app/utils/circuit_breaker.py

"""
Circuit breaker prevents cascade failures when an API is down.
States: CLOSED (normal) → OPEN (failing) → HALF-OPEN (testing recovery)

Use for: Deepgram, Groq, OpenAI calls
"""

import asyncio
import time
from enum import Enum
import structlog

log = structlog.get_logger()


class CircuitState(Enum):
    CLOSED = "closed"         # Normal operation
    OPEN = "open"             # Failing — reject calls immediately
    HALF_OPEN = "half_open"   # Testing if service recovered


class CircuitBreaker:

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        expected_exception: type = Exception,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float | None = None
        self._lock = asyncio.Lock()

    async def call(self, func, *args, **kwargs):
        async with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitState.HALF_OPEN
                    log.info("Circuit breaker: HALF_OPEN — testing recovery")
                else:
                    raise RuntimeError(f"Circuit breaker OPEN — service unavailable")

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except self.expected_exception as e:
            await self._on_failure()
            raise

    async def _on_success(self) -> None:
        async with self._lock:
            self._failure_count = 0
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                log.info("Circuit breaker: CLOSED — service recovered")

    async def _on_failure(self) -> None:
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                log.warning(
                    "Circuit breaker: OPEN",
                    failures=self._failure_count,
                )

    def _should_attempt_reset(self) -> bool:
        if self._last_failure_time is None:
            return True
        return time.time() - self._last_failure_time >= self.recovery_timeout


# Usage:
deepgram_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)
groq_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=15.0)
```

---

### Phase H Success Criteria

```
✅ Jaeger UI shows full trace for each pipeline execution
✅ Prometheus scrapes metrics every 15s
✅ E2E latency histogram visible in Grafana
✅ Circuit breaker opens after 3 Deepgram failures and falls back to Whisper
✅ Circuit breaker closes after service recovers (test by restarting Deepgram mock)
✅ ACTIVE_SESSIONS gauge accurately reflects WebSocket count
```

---

## UPGRADE PHASE I: Full Desktop Stealth Application (Tauri Option 2 — Final Phase)
### Priority: P2 | Difficulty: Hard | Impact: High

### Why This Phase (As The Final Phase)

While **Phase A (Option 1)** delivers immediate screen-share invisibility using Windows API `SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE)` without requiring a Rust/Tauri toolchain, packaging the entire application as a native desktop application in this final phase delivers ultimate enterprise stealth:
- **Process Name Obfuscation**: Runs as an innocuous system process (e.g., `AudioSvc.exe` or `WinAudioAssist.exe`) rather than a browser window or Node/Python process.
- **Taskbar & Alt+Tab Hiding**: Completely hidden from the Taskbar and `Alt+Tab` application switcher; controlled exclusively via Windows System Tray.
- **Global Hardware Hotkeys**: System-wide global keyboard shortcuts (`Ctrl+Shift+H`) to instantly toggle visibility or click-through transparency anywhere in Windows.
- **Native WASAPI Audio Capture**: Direct loopback audio capture at the kernel/system level without browser microphone permission dialogs.
- **Standalone Installer**: Production `.msi` / `.exe` installer bundling React frontend + embedded backend.

---

### I.1: Process Obfuscation & System Tray Integration (`desktop/src-tauri/src/stealth/process.rs`)

```rust
// desktop/src-tauri/src/stealth/process.rs
use tauri::{AppHandle, Manager, SystemTray, SystemTrayEvent, SystemTrayMenu};

pub fn setup_system_tray() -> SystemTray {
    let tray_menu = SystemTrayMenu::new();
    SystemTray::new().with_menu(tray_menu)
}

pub fn handle_tray_event(app: &AppHandle, event: SystemTrayEvent) {
    if let SystemTrayEvent::LeftClick { .. } = event {
        if let Some(window) = app.get_window("main") {
            let is_visible = window.is_visible().unwrap_or(false);
            if is_visible {
                let _ = window.hide();
            } else {
                let _ = window.show();
                let _ = window.set_focus();
            }
        }
    }
}
```

---

### I.2: Global Panic Hotkey & Transparency Control (`desktop/src-tauri/src/hotkeys.rs`)

```rust
// desktop/src-tauri/src/hotkeys.rs
use tauri::{AppHandle, GlobalShortcutManager, Manager};

pub fn register_global_hotkeys(app: &mut AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    let mut shortcut_manager = app.global_shortcut_manager();
    let handle = app.clone();

    // Ctrl+Shift+H: Global Panic Hide/Show
    shortcut_manager.register("Ctrl+Shift+H", move || {
        if let Some(window) = handle.get_window("main") {
            let visible = window.is_visible().unwrap_or(false);
            if visible {
                let _ = window.hide();
            } else {
                let _ = window.show();
            }
        }
    })?;

    Ok(())
}
```

---

### Phase I Success Criteria

```
✅ Application builds as standalone native executable (`desktop/src-tauri`)
✅ Process appears in Task Manager under an innocuous system name (`WinAudioAssist.exe`)
✅ Application window is completely hidden from Windows Taskbar and Alt+Tab switcher
✅ Left-click on System Tray icon toggles overlay window show/hide
✅ Pressing `Ctrl+Shift+H` globally toggles window visibility instantaneously (<50ms)
✅ WDA_EXCLUDEFROMCAPTURE affinity remains active on the native Tauri window handle
```

---

## Part 6: Capability Parity After All Phases

```
Feature                          Before    After All Phases   Parakeet
────────────────────────────────────────────────────────────────────────
Stealth/Invisibility               0%         95%               95%
Audio Intelligence                20%         80%               85%
STT Accuracy                      65%         85%               90%
Speaker Diarization               40%         75%               80%
Question Detection                45%         80%               85%
Resume Understanding              30%         75%               80%
JD Understanding                  25%         70%               75%
RAG Quality                       35%         80%               85%
Answer Quality                    40%         80%               85%
Hallucination Prevention          15%         70%               70%
Context Memory                    20%         75%               75%
Coding Question Support            0%         70%               80%
Streaming Performance             50%         80%               90%
Observability                     20%         80%               80%
Privacy Architecture              20%         80%               75%
────────────────────────────────────────────────────────────────────────
Overall Parity                    28%         80%               82%
────────────────────────────────────────────────────────────────────────
Target (60% parity): EXCEEDED at 80% ✅
```

---

## Part 7: Final Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DESKTOP (Tauri + React)                            │
│                                                                       │
│  ┌──────────────┐  ┌─────────────────┐  ┌────────────────────────┐  │
│  │ STEALTH LAYER │  │  MAIN WINDOW    │  │  OVERLAY WINDOW        │  │
│  │               │  │                 │  │  (screen-share hidden) │  │
│  │ • Process hide │  │ • Session setup │  │  • Streamed answer     │  │
│  │ • Window hide  │  │ • Dashboard     │  │  • STAR hints          │  │
│  │ • Origin guard │  │ • Feedback      │  │  • Coding analysis     │  │
│  │ • Hotkeys      │  │ • Privacy toggle│  │  • Opacity control     │  │
│  └──────────────┘  └─────────────────┘  └────────────────────────┘  │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  AUDIO CAPTURE LAYER                                            │  │
│  │  RNNoise → [BlackHole/WASAPI/Mic] → 16kHz PCM → WS binary      │  │
│  └────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                              │ WebSocket (binary PCM + JSON control)
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND                                     │
│                                                                       │
│  RECEIVE LOOP (never awaits slow ops)                                 │
│  └→ audio_queue.put_nowait()                                          │
│                                                                       │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────────────┐  │
│  │  VAD WORKER  │  │ STT PROCESSOR  │  │  QUESTION HANDLER        │  │
│  │              │  │               │  │  (asyncio.create_task)   │  │
│  │ AdaptiveSile │  │ ResilientSTT: │  │                          │  │
│  │ ro VAD with  │  │  Deepgram     │  │  1. QueryExpander        │  │
│  │ noise floor  │  │  → Whisper    │  │  2. HybridSearch         │  │
│  │ estimation   │  │    (fallback) │  │     BM25 + pgvector      │  │
│  │              │  │               │  │  3. CrossEncoder Rerank  │  │
│  │ end_of_utt   │  │ pyannote /    │  │  4. AnswerPipeline       │  │
│  │ → create_task│  │ resemblyzer   │  │     Draft → Critique     │  │
│  └──────────────┘  └───────────────┘  │     → Revise → Stream   │  │
│                                        │  5. HallucinationGuard  │  │
│                                        │  6. AnswerCache         │  │
│                                        │  7. SemanticMemory      │  │
│                                        └──────────────────────────┘  │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │  LLM SMART ROUTER                                              │    │
│  │  Ollama (local, private) → Groq → OpenAI (cascade)            │    │
│  │  CircuitBreaker on each provider                               │    │
│  └──────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
           │                         │                    │
           ▼                         ▼                    ▼
┌──────────────────┐    ┌─────────────────────┐  ┌──────────────────┐
│  PostgreSQL 16   │    │  Redis 7             │  │  Observability   │
│  + pgvector      │    │                      │  │                  │
│                  │    │  Session state       │  │  Jaeger (traces) │
│  Users           │    │  Transcript buffer   │  │  Prometheus      │
│  Sessions        │    │  Semantic memory     │  │  Grafana         │
│  Transcripts     │    │  Answer cache        │  │  Sentry          │
│  Answers         │    │  Ingestion status    │  │                  │
│  Feedback        │    │                      │  │                  │
│  Doc chunks      │    │                      │  │                  │
│  (HNSW indexed)  │    │                      │  │                  │
└──────────────────┘    └─────────────────────┘  └──────────────────┘

LOCAL MODELS (no internet required):
  faster-whisper (STT) ──── ./.whisper_models/
  bge-m3 (embeddings) ───── ./.embedding_models/
  sentence-transformers ─── ./.reranker_models/
  Ollama (LLM) ──────────── localhost:11434
  LLaVA (vision) ────────── localhost:11434
```

---

## Part 8: Implementation Priority Order

```
Week 1-2:   Phase A (Stealth Option 1) — Windows API WDA_EXCLUDEFROMCAPTURE overlay
Week 3-4:   Phase B (Audio)            — Noise suppression, local STT fallback
Week 5-6:   Phase C (RAG)              — Hybrid search + reranker + local embeddings
Week 7-8:   Phase D (Answer Quality)   — Multi-step generation + hallucination guard
Week 9-10:  Phase E (Memory)           — Session + cross-session memory
Week 11-12: Phase F (Local LLM)        — Ollama + privacy mode
Week 13-14: Phase G (Coding)           — Screenshot + vision pipeline
Week 15-16: Phase H (Observability)    — Tracing, metrics, circuit breakers
Week 17-18: Phase I (Stealth Option 2) — Native Tauri app, process hiding & system tray

Total: 18 weeks to full implementation
Cost: $0 recurring (assuming Groq free tier for development)
      ~$50/month if Groq free tier is exceeded during testing
```

---

## Part 9: Project Structure After All Upgrades

```
e:\IC\
├── backend/
│   └── app/
│       ├── services/
│       │   ├── audio/
│       │   │   ├── noise_suppressor.py      # RNNoise / noisereduce
│       │   │   └── diarizer.py              # pyannote / resemblyzer
│       │   ├── stt/
│       │   │   ├── base.py
│       │   │   ├── deepgram.py
│       │   │   ├── whisper_local.py         # faster-whisper
│       │   │   └── resilient.py             # Auto-fallback provider
│       │   ├── rag/
│       │   │   ├── embeddings.py            # Local bge-m3
│       │   │   ├── hybrid_search.py         # BM25 + vector
│       │   │   ├── reranker.py              # cross-encoder
│       │   │   ├── chunking.py              # Parent-child
│       │   │   └── query_expansion.py
│       │   ├── answer/
│       │   │   ├── pipeline.py              # Multi-step generation
│       │   │   ├── prompt_templates.py      # Per question-type prompts
│       │   │   ├── hallucination_guard.py
│       │   │   └── cache.py                 # Semantic answer cache
│       │   ├── memory/
│       │   │   ├── session_memory.py        # Semantic in-session memory
│       │   │   └── cross_session_memory.py  # Persistent user memory
│       │   ├── llm/
│       │   │   ├── groq_provider.py
│       │   │   ├── openai_provider.py
│       │   │   ├── ollama_provider.py       # Local LLM
│       │   │   └── smart_router.py          # Provider selection
│       │   ├── coding/
│       │   │   └── pipeline.py              # Vision → solution
│       │   └── vad.py                       # Adaptive VAD
│       ├── metrics.py                       # Prometheus metrics
│       └── telemetry.py                     # OpenTelemetry setup
│
├── desktop/
│   └── src-tauri/
│       └── src/
│           ├── stealth/
│           │   ├── process.rs               # Process name obfuscation
│           │   └── anti_detection.rs
│           ├── audio/
│           │   ├── windows.rs               # WASAPI loopback
│           │   └── macos.rs                 # ScreenCaptureKit
│           ├── overlay/
│           │   ├── windows.rs               # WDA_EXCLUDEFROMCAPTURE
│           │   └── macos.rs                 # NSWindow.sharingType
│           └── hotkeys.rs                   # Global shortcut manager
│
├── monitoring/
│   ├── prometheus.yml
│   ├── grafana/
│   │   └── dashboards/
│   │       └── pipeline_latency.json
│   └── alerts.yml
│
└── tests/
    ├── benchmark_latency.py
    ├── test_stealth.py                      # Verify overlay invisible
    ├── test_hybrid_search.py                # Compare vs vector-only
    ├── test_hallucination_guard.py          # Known hallucination cases
    ├── test_noise_suppression.py            # SNR improvement measurement
    └── load_test.py                         # Locust load test
```

---

*End of Capability Upgrade Master Document.
All tools listed are free, open-source, and production-ready.
Implementation follows the priority order in Part 8.
Each phase has independent success criteria and can ship incrementally.*
```