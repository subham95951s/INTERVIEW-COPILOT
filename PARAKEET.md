Interview Copilot AI — Complete System Design Document
Markdown

# InterviewCopilot AI
### Product Requirements Document & System Architecture
**Version:** 1.0
**Status:** Draft
**Last Updated:** 2025

---

## Table of Contents
1. [Product Overview](#1-product-overview)
2. [Goals & Non-Goals](#2-goals--non-goals)
3. [User Personas & Use Cases](#3-user-personas--use-cases)
4. [Functional Requirements](#4-functional-requirements)
5. [Non-Functional Requirements](#5-non-functional-requirements)
6. [System Architecture](#6-system-architecture)
7. [Component Design](#7-component-design)
8. [Data Model](#8-data-model)
9. [API Specification](#9-api-specification)
10. [Latency Budget](#10-latency-budget)
11. [Security & Privacy](#11-security--privacy)
12. [Tech Stack](#12-tech-stack)
13. [Infrastructure & Deployment](#13-infrastructure--deployment)
14. [Cost Model](#14-cost-model)
15. [Risks & Mitigations](#15-risks--mitigations)
16. [Roadmap & Milestones](#16-roadmap--milestones)
17. [Success Metrics](#17-success-metrics)
18. [Open Questions](#18-open-questions)

---

## 1. Product Overview

### 1.1 Summary
InterviewCopilot AI is a desktop application that listens to a live interview conversation (video call or in-person), transcribes speech in real-time, detects when the interviewer asks a question, and generates a personalized, context-aware answer using the candidate's resume and the job description — displayed on a discreet, screen-share-invisible overlay.

### 1.2 Problem Statement
Candidates often freeze under pressure, forget relevant experience, or fail to structure answers clearly (e.g., STAR format) — even when they are objectively qualified for the role.

### 1.3 Positioning (Choose One — Critical Decision)

| Mode | Description | Legal/Ethical Risk | Recommended |
|---|---|---|---|
| **A. Live Stealth Mode** | Real-time answers during actual interviews, hidden from screen share | High — may violate platform ToS, employer trust, some jurisdictions | ⚠️ Not recommended as primary positioning |
| **B. Mock Practice Mode** | Simulated interviews with AI feedback, no deception involved | None | ✅ Recommended MVP |
| **C. Post-call Coaching** | Records practice sessions, gives structured feedback afterward | None | ✅ Recommended |
| **D. Transparent Co-pilot** | Used openly (e.g., internal training, non-native speaker support, accessibility) | Low | ✅ Viable differentiator |

> **Recommendation:** Build the full real-time technical pipeline (it's identical for all 4 modes), but launch and market as **Mock Interview Practice + Real-Time Coaching**, with an optional "Live Assist" mode gated behind a clear disclaimer for accessibility/non-native speaker use cases. This avoids ToS/legal exposure while still solving the core technical problem.

### 1.4 Target Platforms
- macOS (primary — most common for tech interviews)
- Windows (secondary)
- Web (practice-mode only, no system-audio capture needed)

---

## 2. Goals & Non-Goals

### 2.1 Goals
- G1: Transcribe live conversation with < 1s latency
- G2: Detect interview questions with > 90% precision, < 10% false positive rate
- G3: Generate personalized answers grounded in resume/JD within 2s of question completion
- G4: Provide a distraction-minimal UI (overlay or dashboard)
- G5: Support both live and practice/mock modes

### 2.2 Non-Goals (v1)
- NG1: Not building a full ATS or job-application platform
- NG2: Not supporting group interviews / multi-speaker panels (v1 = 1 interviewer + 1 candidate)
- NG3: Not supporting non-English languages (v1 = English only)
- NG4: Not building proprietary STT/LLM models — using third-party APIs

---

## 3. User Personas & Use Cases

### 3.1 Personas

**P1 — Anxious Job Seeker**
Mid-level engineer, strong technically, freezes up in live interviews, wants a safety net.

**P2 — Non-Native English Speaker**
Strong domain skills, struggles to articulate answers fluently in real-time in a second language.

**P3 — Career Switcher**
Has transferable skills but struggles to map past experience to new role's language/keywords.

### 3.2 Core Use Cases
| ID | Use Case | Priority |
|---|---|---|
| UC1 | Upload resume + JD before a mock interview | P0 |
| UC2 | Run a simulated interview with AI-generated questions | P0 |
| UC3 | Get real-time suggested talking points during simulated interview | P0 |
| UC4 | Review post-interview transcript + feedback report | P0 |
| UC5 | Live-assist during an actual call (opt-in, disclosed mode) | P1 |
| UC6 | Coding question detection → structured approach + pseudocode | P1 |
| UC7 | Multi-session history / progress tracking | P2 |

---

## 4. Functional Requirements

### 4.1 Onboarding
- FR1.1: User signs up (email/OAuth)
- FR1.2: User uploads resume (PDF/DOCX)
- FR1.3: User pastes/uploads job description
- FR1.4: System parses & embeds documents into vector store within 10s

### 4.2 Session Setup
- FR2.1: User selects mode: Mock Interview / Live Assist
- FR2.2: User selects interview type: Behavioral / Technical / System Design / Coding
- FR2.3: System initializes session context (resume + JD embeddings + interview type)

### 4.3 Real-Time Pipeline
- FR3.1: Capture audio (mic + system audio for Live mode; mic + TTS interviewer for Mock mode)
- FR3.2: Stream audio to STT engine, produce rolling transcript
- FR3.3: Detect speaker turns (diarization)
- FR3.4: Detect completed questions via VAD + classifier
- FR3.5: Retrieve relevant resume/JD chunks via vector search
- FR3.6: Generate streamed answer via LLM
- FR3.7: Render answer in overlay/UI within latency budget
- FR3.8: For coding questions: capture screenshot → vision model → structured response

### 4.4 Post-Session
- FR4.1: Generate full transcript
- FR4.2: Generate feedback report (clarity, structure, keyword alignment with JD, filler word count)
- FR4.3: Store session history per user

### 4.5 Overlay (Live Assist mode only)
- FR5.1: Always-on-top, transparent, click-through window
- FR5.2: Hidden from screen share / recording APIs
- FR5.3: Hotkey to show/hide, scroll, resize
- FR5.4: Hotkey to manually re-trigger last question (in case of misdetection)

---

## 5. Non-Functional Requirements

| Category | Requirement |
|---|---|
| **Latency** | < 1.5s from end-of-question to first token displayed |
| **Availability** | 99.5% uptime for backend services |
| **Scalability** | Support 1,000 concurrent live sessions at launch scale |
| **Accuracy** | STT WER (word error rate) < 10% in clean audio conditions |
| **Privacy** | Audio not stored by default; opt-in only for transcript retention |
| **Security** | All data encrypted in transit (TLS 1.3) and at rest (AES-256) |
| **Compatibility** | macOS 12+, Windows 10+, Chrome/Edge for web practice mode |
| **Cost Efficiency** | < $0.15 per 10-minute live session (API costs) |

---

## 6. System Architecture

### 6.1 High-Level Architecture Diagram
┌─────────────────────────────────────────────────────────────────┐
│ CLIENT (Desktop App) │
│ Tauri (Rust) + React Frontend │
│ │
│ ┌───────────────┐ ┌──────────────┐ ┌────────────────────┐ │
│ │ Audio Capture │ │ Overlay UI │ │ Session Dashboard │ │
│ │ (WASAPI/ │ │ (transparent,│ │ (setup, history, │ │
│ │ CoreAudio) │ │ click-through)│ │ feedback reports) │ │
│ └───────┬───────┘ └──────┬───────┘ └──────────┬──────────┘ │
│ │ ▲ │ │
└──────────┼──────────────────┼───────────────────────┼──────────────┘
│ WebSocket │ WebSocket │ REST/HTTPS
│ (audio chunks) │ (streamed answers) │ (auth, CRUD)
▼ │ ▼
┌─────────────────────────────────────────────────────────────────┐
│ API GATEWAY (FastAPI) │
│ Auth, Rate Limiting, Routing │
└──────┬─────────────┬──────────────┬───────────────┬──────────────┘
│ │ │ │
▼ ▼ ▼ ▼
┌───────────┐ ┌─────────────┐ ┌──────────┐ ┌──────────────┐
│ STT │ │ VAD / │ │ RAG │ │ LLM Router │
│ Service │→ │ Question │→ │ Service │→ │ (Groq/OpenAI│
│ (Deepgram/ │ │ Detector │ │(ChromaDB/│ │ /Anthropic) │
│ Whisper) │ │ (Silero+ │ │ pgvector)│ │ │
│ │ │ small LLM) │ │ │ │ │
└───────────┘ └─────────────┘ └──────────┘ └──────────────┘
│ │
▼ ▼
┌───────────────────┐ ┌─────────────────────┐
│ Session State │ │ Document Parser │
│ (Redis) │ │ (PDF/DOCX → chunks │
│ - transcript buf │ │ → embeddings) │
│ - Q&A history │ └─────────────────────┘
└───────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ PERSISTENT STORAGE LAYER │
│ PostgreSQL (users, sessions, transcripts, feedback reports) │
│ Object Storage / S3 (resumes, JDs, optional audio recordings) │
│ Vector DB (pgvector or standalone ChromaDB) — resume/JD chunks │
└─────────────────────────────────────────────────────────────────┘

text


### 6.2 Data Flow — Live Session (Sequence)
Interviewer speaks
│
▼
[Audio Capture] → PCM chunks (250ms) → WebSocket → [STT Service]
│
▼
Rolling transcript + VAD end-of-speech signal
│
▼
[Question Detector] (Groq Llama-3-8B, ~100ms)
│ is_question == true
▼
[RAG Retrieval] → top-k resume/JD chunks (pgvector similarity search)
│
▼
[Prompt Assembly] → system prompt + context + last N Q&A + question
│
▼
[LLM Router] → Groq Llama-3.3-70B (streamed tokens)
│
▼
WebSocket → [Overlay UI] renders tokens as they arrive

text


---

## 7. Component Design

### 7.1 Audio Capture Layer
| Platform | Method | Notes |
|---|---|---|
| macOS | ScreenCaptureKit (system audio) + AVAudioEngine (mic) | Requires screen-recording permission |
| Windows | WASAPI loopback (system audio) + mic API | No special permission needed for loopback |
| Web (practice mode) | `getUserMedia` only | No system audio needed since interviewer is simulated TTS/text |

**Output:** 16kHz mono PCM, 250ms frames, sent over WebSocket as binary frames.

### 7.2 STT Service
- Abstraction layer (`STTProvider` interface) supporting:
  - `DeepgramProvider` (default, streaming, diarization built-in)
  - `WhisperProvider` (self-hosted fallback, faster-whisper + pyannote for diarization)
- Returns: partial transcripts (interim) + final transcripts (confirmed) + speaker labels

### 7.3 VAD + Question Detection
Silero VAD → detects silence > 1.0s after speech
│
▼
Buffer last 15s of transcript (speaker = interviewer only)
│
▼
Groq Llama-3-8B classifier call:
Prompt: "Given this transcript snippet, is the last utterance a
complete question directed at the candidate? Return JSON:
{is_question: bool, confidence: float, cleaned_question: string}"
│
▼
If is_question && confidence > 0.7 → trigger RAG pipeline

text


### 7.4 RAG Service
- **Ingestion (session setup):**
  1. Parse resume (PDF/DOCX → text) using `pdfplumber` / `python-docx`
  2. Chunk by semantic section (Experience, Projects, Skills, Education)
  3. Embed via `text-embedding-3-small` (OpenAI) or local `bge-small-en`
  4. Store in pgvector table scoped by `session_id`
- **Retrieval (per question):**
  1. Embed incoming question
  2. Cosine similarity search, top-k = 4
  3. Return chunks + metadata (source section)

### 7.5 LLM Answer Generation
**System Prompt Template:**
You are helping {candidate_name} answer an interview question in real-time.
Respond in first person, as if the candidate is speaking.
Keep answers concise (30-60 seconds spoken length, ~100-150 words)
unless the question requires more depth (system design, coding).
Use the STAR format for behavioral questions.
Ground your answer in the candidate's actual background below —
do not fabricate experience not present in the context.

Candidate Background (retrieved context):
{rag_chunks}

Job Description Highlights:
{jd_summary}

Recent conversation:
{last_3_qa_pairs}

Current Question:
{question}

text


### 7.6 Overlay Rendering (Live Assist Mode)
| OS | Mechanism |
|---|---|
| macOS | `NSWindow.sharingType = .none` via Tauri's `raw-window-handle` + Objective-C bridge |
| Windows | `SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)` via Rust `windows` crate |

**UI behavior:**
- Transparent background, 70% opacity text panel
- Click-through by default (`WS_EX_TRANSPARENT` on Windows / `ignoresMouseEvents` on Mac)
- Global hotkey (e.g., `Cmd+Shift+H`) toggles interactive mode for scrolling

### 7.7 Coding Question Pipeline
Screenshot capture (hotkey-triggered)
│
▼
Vision-capable LLM (GPT-4o / Claude 3.5 Sonnet)
│
▼
Structured JSON output:
{
"problem_summary": "...",
"approach": "...",
"pseudocode": "...",
"time_complexity": "...",
"space_complexity": "...",
"edge_cases": ["..."]
}
│
▼
Rendered in overlay as formatted code block

text


---

## 8. Data Model

### 8.1 PostgreSQL Schema (Core Tables)

```sql
-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    plan TEXT DEFAULT 'free' -- free, pro, enterprise
);

-- Resumes
CREATE TABLE resumes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    file_url TEXT,
    parsed_text TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Job Descriptions
CREATE TABLE job_descriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    raw_text TEXT,
    company_name TEXT,
    role_title TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Sessions
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    resume_id UUID REFERENCES resumes(id),
    jd_id UUID REFERENCES job_descriptions(id),
    mode TEXT CHECK (mode IN ('mock', 'live_assist')),
    interview_type TEXT CHECK (interview_type IN ('behavioral','technical','system_design','coding')),
    started_at TIMESTAMPTZ DEFAULT now(),
    ended_at TIMESTAMPTZ,
    status TEXT DEFAULT 'active'
);

-- Transcript entries
CREATE TABLE transcript_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id),
    speaker TEXT CHECK (speaker IN ('interviewer','candidate')),
    text TEXT,
    timestamp_ms INTEGER,
    is_question BOOLEAN DEFAULT false
);

-- Generated answers
CREATE TABLE generated_answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id),
    question_text TEXT,
    answer_text TEXT,
    latency_ms INTEGER,
    retrieved_chunks JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Feedback reports
CREATE TABLE feedback_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id),
    clarity_score FLOAT,
    structure_score FLOAT,
    keyword_alignment_score FLOAT,
    filler_word_count INTEGER,
    summary TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
8.2 Vector Store Schema (pgvector)
SQL

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id),
    source_type TEXT CHECK (source_type IN ('resume','jd')),
    section TEXT, -- e.g. 'experience', 'skills'
    chunk_text TEXT,
    embedding VECTOR(1536),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ON document_chunks USING ivfflat (embedding vector_cosine_ops);
8.3 Redis (Session State — Ephemeral)
text

Key: session:{session_id}:transcript_buffer  → List (rolling last 30s)
Key: session:{session_id}:qa_history         → List (last 5 Q&A pairs)
Key: session:{session_id}:status             → String (active/paused/ended)
TTL: 4 hours
9. API Specification
9.1 REST Endpoints
Method	Endpoint	Description
POST	/auth/signup	Create user account
POST	/auth/login	Authenticate, return JWT
POST	/resumes	Upload & parse resume
POST	/job-descriptions	Submit JD text
POST	/sessions	Create new session (mock/live)
GET	/sessions/{id}	Get session details
POST	/sessions/{id}/end	End session, trigger feedback generation
GET	/sessions/{id}/transcript	Get full transcript
GET	/sessions/{id}/feedback	Get feedback report
GET	/sessions	List user's session history
9.2 WebSocket Protocol
Endpoint: wss://api.interviewcopilot.ai/ws/session/{session_id}

Client → Server messages:

JSON

// Binary frame: raw PCM audio chunk
// OR control messages:
{ "type": "control", "action": "pause" }
{ "type": "control", "action": "resume" }
{ "type": "manual_trigger", "text": "re-answer last question" }
{ "type": "screenshot", "data": "base64_image" }
Server → Client messages:

JSON

{ "type": "transcript_partial", "speaker": "interviewer", "text": "..." }
{ "type": "transcript_final", "speaker": "interviewer", "text": "...", "is_question": true }
{ "type": "answer_token", "token": "I " }
{ "type": "answer_complete", "full_text": "...", "latency_ms": 1240 }
{ "type": "error", "message": "..." }
10. Latency Budget
Stage	Target Latency	Notes
Audio chunk → server	50ms	Network/WebSocket overhead
STT (streaming)	200-300ms	Deepgram Nova-2
VAD silence detection	1000ms	Configurable pause threshold
Question classification	100ms	Groq Llama-3-8B
Vector retrieval	50ms	pgvector, local index
LLM TTFT (time to first token)	300-500ms	Groq Llama-3.3-70B
Render in UI	20ms	WebSocket push
Total (post-silence)	~1.5-2s	Before full answer is streaming
11. Security & Privacy
11.1 Data Handling
Audio: processed in-memory, not persisted by default
Transcripts: stored only if user opts in (for feedback reports); auto-deleted after 30 days on free tier
Resumes/JDs: encrypted at rest (AES-256), scoped per-user with row-level security
11.2 Compliance Considerations
GDPR: right to deletion, data export endpoints required
Wiretapping laws: critical — some jurisdictions (e.g., certain US states) require all-party consent to record conversations. Live Assist mode must:
Display clear consent disclaimer
Possibly notify the other party depending on jurisdiction
Legal review required before launch in "Live Assist" mode
11.3 Application Security
JWT-based auth with short-lived access tokens + refresh tokens
Rate limiting on all endpoints (per-user, per-IP)
WebSocket connections authenticated via signed session tokens
All secrets (API keys) managed via environment/secret manager, never client-side
12. Tech Stack
Layer	Technology	Rationale
Desktop shell	Tauri (Rust)	Smaller binary, easier native OS API access than Electron
Frontend	React + TypeScript + TailwindCSS	Fast iteration, familiar ecosystem
Backend API	FastAPI (Python)	Async support, WebSocket-native, fast to prototype
STT	Deepgram (primary), faster-whisper (self-hosted fallback)	Latency + diarization
VAD	Silero VAD	Lightweight, accurate, runs client or server side
LLM (fast path)	Groq (Llama 3.3 70B)	Fastest inference for real-time UX
LLM (quality path)	OpenAI GPT-4.1 / Claude 3.5 Sonnet	User-selectable for non-time-critical (mock mode)
Vector DB	pgvector (Postgres extension)	Avoids extra infra vs. standalone ChromaDB
Relational DB	PostgreSQL	Reliable, supports pgvector natively
Session cache	Redis	Fast ephemeral state
Object storage	S3 / Cloudflare R2	Resume/JD file storage
Auth	Clerk / Auth0 or custom JWT	Speed of integration
Hosting	Fly.io / Railway (MVP) → AWS/GCP (scale)	Fast MVP deploy, WebSocket-friendly
13. Infrastructure & Deployment
13.1 MVP Deployment (Low Scale)
text

Fly.io / Railway
  ├── FastAPI backend (autoscaling, 2-4 instances)
  ├── Redis (managed)
  ├── PostgreSQL + pgvector (managed, e.g. Supabase/Neon)
  └── S3-compatible storage (Cloudflare R2)

Client distributed via:
  ├── Direct download (DMG/EXE) from marketing site
  └── Auto-update via Tauri's built-in updater
13.2 Scale Considerations (Post-PMF)
Move STT/VAD to dedicated GPU instances if self-hosting Whisper (AWS g5 instances)
Horizontal scaling of WebSocket handlers behind a load balancer with sticky sessions
Consider dedicated region deployment for latency-sensitive users (US/EU/APAC)
13.3 CI/CD
GitHub Actions: lint → test → build → deploy
Tauri auto-build pipeline for Mac (notarization) + Windows (code signing) — required, unsigned apps trigger OS security warnings
14. Cost Model (Per Session Estimate)
Assumptions: 10-minute session, ~10 questions asked

Component	Cost
Deepgram STT (10 min @ $0.0043/min)	$0.043
Question classification (Groq, ~10 calls, 8B model)	~$0.002
Embedding retrieval (negligible, local)	~$0.00
Answer generation (Groq 70B, ~10 calls x 200 tokens)	~$0.02
Total per session	~$0.07-0.10
At 10,000 sessions/month: ~$700-1000/month in inference costs — supports a pricing model of $15-30/month per user comfortably.

15. Risks & Mitigations
Risk	Impact	Mitigation
Legal/ToS violation (Live Assist misuse)	High	Position as practice tool by default; consent disclaimers; legal review
Proctoring software detects overlay	Medium	Continuous R&D on detection evasion; accept some cat-and-mouse dynamic
STT inaccuracy in noisy environments	Medium	Allow manual text correction; noise suppression preprocessing (RNNoise)
LLM hallucinates false experience	High	Strict RAG grounding; system prompt constraints; user review before "trusting" answers
High API costs at scale	Medium	Cache common Q&A patterns; tiered pricing; self-host STT at scale
False positive question detection	Medium	Confidence threshold tuning; manual override hotkey
Platform bans (app stores)	Medium	Distribute via direct download, not App Store, for Live Assist features
16. Roadmap & Milestones
Phase 0 — Core Pipeline Validation (2-3 weeks)
 FastAPI WebSocket server + audio streaming
 Deepgram integration, live transcript display
 Silero VAD integration
 Question classifier (Groq) working end-to-end
 Milestone: < 1.5s latency demo, terminal/basic UI only
Phase 1 — RAG + Answer Generation (2 weeks)
 Resume/JD upload + parsing + chunking
 pgvector integration
 Prompt template + Groq streaming integration
 Milestone: Full pipeline working in browser (mock mode, text-based)
Phase 2 — Practice Mode Product (3-4 weeks)
 AI interviewer (TTS + generated questions) for mock sessions
 Session dashboard, history, feedback reports
 Web app launch (no desktop needed for this mode)
 Milestone: Public beta launch — Mock Interview Practice tool
Phase 3 — Desktop + Live Assist (4-6 weeks)
 Tauri desktop shell
 Native audio capture (WASAPI/CoreAudio)
 Overlay window with screen-share exclusion
 Legal review + consent flow
 Milestone: Live Assist beta (invite-only, disclosed use cases)
Phase 4 — Polish & Scale
 Coding question vision pipeline
 Multi-language support
 Self-hosted STT for cost optimization
 Enterprise/team plans
17. Success Metrics
Metric	Target (3 months post-launch)
Weekly active users	1,000+
Mock interview completion rate	> 60%
Avg. session latency (p95)	< 2s
User-reported "helped me get an offer"	Track via post-interview survey
Free → paid conversion	> 5%
Churn (monthly)	< 8%
18. Open Questions
Do we build our own AI-interviewer (TTS + dynamic questioning) for mock mode, or license an existing conversational AI framework?
What's the legal exposure by region for "Live Assist" — needs formal legal counsel review before that phase ships.
Should diarization be mandatory (added cost) or optional based on plan tier?
Do we support Linux for the desktop app, given likely low demand vs. engineering cost?
Pricing model — flat subscription vs. per-session credits vs. usage-based?
End of document.

text


---

This is a complete, buildable spec. A few notes on how to use it:

- **Section 6-9** (Architecture, Components, Data Model, API) are what you'd hand directly to engineers to start building
- **Section 16** (Roadmap) gives you a realistic sequencing — I'd strongly recommend starting at **Phase 0** exactly as scoped, since validating the latency pipeline is the highest-risk, most technically uncertain part
- **Section 1.3 and Section 11.2** are the parts I'd genuinely pause on — the "Live Assist" positioning has real legal exposure depending on your target market's jurisdiction (wiretapping/consent laws vary a lot by US state and by country)
