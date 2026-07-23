# InterviewCopilot AI 🚀
**InterviewCopilot AI** is a low-latency, real-time AI interview assistant and practice platform. It captures audio during interview sessions (live interviews or practice sessions), transcribes speech in real-time, detects structured questions via voice activity detection (VAD) and semantic classification, and instantly synthesizes personalized **STAR-format** (Situation, Task, Action, Result) answers backed by candidate resumes and job description evidence.
---
## ✨ Features
*   **Real-Time Speech-to-Text (STT):** Continuous streaming transcription with speaker diarization using Deepgram Nova-2.
*   **Intelligent End-of-Utterance & Question Detection:** Combines neural Voice Activity Detection (`SileroVAD`) and NLP rule/classifier pipelines (`QuestionDetector`) to reliably distinguish conversational chatter from interview prompts.
*   **Low-Latency RAG Engine:** Retrieves top matching chunks from candidate resumes (`pgvector` cosine similarity) and job descriptions to ground LLM responses in real candidate achievements.
*   **Token-by-Token Answer Streaming:** Streams structured answers over WebSockets from high-throughput LLMs (`Groq Llama-3-70B` or `OpenAI GPT-4o`).
*   **Interactive Practice & Coaching:** Provides mock interviews, floating HUD compact overlays, and post-session evaluation scoring.
---
## 🛠️ Technology Stack
*   **Frontend:** React 18, TypeScript, Vite, Tailwind CSS
*   **Backend:** Python, FastAPI, asyncio
*   **AI/ML:**
    *   **LLM:** Groq (Llama-3-70B), OpenAI (GPT-4o, embeddings)
    *   **STT:** Deepgram Nova-2
    *   **VAD:** SileroVAD (PyTorch)
*   **Data & State:** PostgreSQL 16 (with `pgvector`), Redis 7
*   **Real-Time:** WebSockets for bidirectional low-latency streaming
---
## 🚀 Getting Started
### Prerequisites
*   Docker and Docker Compose
*   Node.js (v18+)
*   Python (3.10+)
*   API Keys for Deepgram, Groq, and OpenAI.
### 1. Clone the repository
```bash
git clone <repository-url>
cd IC
```
### 2. Environment Setup
Copy the example environment file and fill in your API keys and configuration.
```bash
cp .env.example .env
```
Ensure you have the following keys properly configured in `.env`:
*   `DEEPGRAM_API_KEY`
*   `GROQ_API_KEY`
*   `OPENAI_API_KEY`
### 3. Run with Docker Compose
The easiest way to start the backend, PostgreSQL (with pgvector), and Redis is using Docker Compose.
```bash
docker-compose up --build -d
```
*This will expose the FastAPI backend at `http://localhost:8000`.*
### 4. Run Frontend Locally
In a separate terminal, navigate to the frontend directory and start the Vite development server.
```bash
cd frontend
npm install
npm run dev
```
*The frontend will be available at `http://localhost:5173`.*
### (Alternative) Running Backend Locally without Docker
If you prefer to run the backend natively:
```bash
cd backend
python -m venv .venv
# Activate venv (Windows)
.\.venv\Scripts\activate
# Activate venv (Mac/Linux)
# source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
*Note: You will still need a running PostgreSQL instance with pgvector and a Redis instance.*
---
## 🏗️ Architecture Overview
The system is designed for sub-millisecond responsiveness during live interviews:
1.  **Frontend Audio Capture:** The browser captures 16kHz mono audio and streams PCM data over WebSockets.
2.  **Streaming STT:** The FastAPI WebSocket gateway pipes audio to Deepgram for live transcription.
3.  **VAD & NLP:** Utterances are analyzed to detect if an interviewer asked a question.
4.  **RAG Context:** Upon question detection, the backend searches PostgreSQL `pgvector` for relevant resume/JD chunks.
5.  **LLM Generation:** The context is sent to a high-speed LLM (Groq), which streams tokens back to the frontend in real-time.
For a detailed deep-dive into the architecture, WebSocket protocols, and data models.
---

