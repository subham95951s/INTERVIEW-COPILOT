import React, { useState, useEffect, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Mic, MicOff, Clock, ChevronRight, Sparkles, ArrowLeft, Zap, ShieldCheck, CheckCircle2, AlertTriangle, Layers, Brain, Code, Headphones, Eye, Monitor } from 'lucide-react'
import { useWebSocket, WSMessage, MemoryContextData, CodingProblemAnalysis } from '../hooks/useWebSocket'
import { CodingOverlay } from '../components/CodingOverlay'
import { useAudioCapture } from '../hooks/useAudioCapture'
import { useSmartOCR } from '../hooks/useSmartOCR'
import { useAuth } from '../context/AuthContext'
import clsx from 'clsx'

interface TranscriptEntry {
  id: string
  speaker: string
  text: string
  isQuestion: boolean
  timestamp: number
  isPartial?: boolean
}

interface AnswerEntry {
  id: string
  question: string
  text: string
  draftText?: string
  revisedText?: string
  activeTab?: 'revised' | 'draft'
  questionType?: string
  confidence?: number
  starScores?: Record<string, number>
  hallucinationRisk?: string
  isCached?: boolean
  isRevised?: boolean
  isRevising?: boolean
  latencyMs: number | null
  isStreaming: boolean
  memoryContext?: MemoryContextData
  cheatSheet?: string[]
  predictedFollowUps?: string[]
}

export default function InterviewPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const { token } = useAuth()
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([])
  const [answers, setAnswers] = useState<AnswerEntry[]>([])
  const [currentStreamingId, setCurrentStreamingId] = useState<string | null>(null)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [lastLatency, setLastLatency] = useState<number | null>(null)
  const [speechTelemetry, setSpeechTelemetry] = useState<{
    wpm: number
    pacingStatus: 'optimal' | 'fast' | 'slow'
    fillerCount: number
    fillerRate: number
  }>({ wpm: 0, pacingStatus: 'optimal', fillerCount: 0, fillerRate: 0 })
  const [lastCodingAnalysis, setLastCodingAnalysis] = useState<CodingProblemAnalysis | null>(null)
  const [isClickThrough, setIsClickThrough] = useState(false)
  const [pipTab, setPipTab] = useState<'answers' | 'transcript' | 'both'>('answers')
  const [shieldMode, setShieldMode] = useState<number>(0x11)
  const [enableLoopback, setEnableLoopback] = useState(false)
  const fileInputRef = React.useRef<HTMLInputElement | null>(null)

  const { connected, sendBinary, sendCodingScreenshot, onMessage } = useWebSocket(sessionId ?? null, token)

  const handlePCMChunk = useCallback((chunk: ArrayBuffer) => {
    sendBinary(chunk)
  }, [sendBinary])

  const { isRecording, isLoopbackActive, start, stop } = useAudioCapture(handlePCMChunk)
  const { isEnabled: isAutoOCR, toggle: toggleAutoOCR, isProcessing: isOCRProcessing } = useSmartOCR({
    onSignificantChange: (base64) => sendCodingScreenshot(base64)
  })



  // Handle incoming WebSocket messages
  useEffect(() => {
    const unsubscribe = onMessage((msg: WSMessage) => {
      switch (msg.type) {
        case 'transcript_partial': {
          setTranscript(prev => {
            const last = prev[prev.length - 1]
            if (last && last.isPartial) {
              return [
                ...prev.slice(0, -1),
                { ...last, text: msg.text, speaker: msg.speaker }
              ]
            }
            return [
              ...prev,
              {
                id: crypto.randomUUID(),
                speaker: msg.speaker,
                text: msg.text,
                isQuestion: false,
                timestamp: Date.now(),
                isPartial: true,
              }
            ]
          })
          break
        }

        case 'transcript_final': {
          const entry: TranscriptEntry = {
            id: crypto.randomUUID(),
            speaker: msg.speaker,
            text: msg.text,
            isQuestion: msg.is_question,
            timestamp: Date.now(),
            isPartial: false,
          }
          setTranscript(prev => {
            const last = prev[prev.length - 1]
            if (last && last.isPartial) {
              return [...prev.slice(0, -1), entry]
            }
            return [...prev, entry]
          })

          if (msg.is_question) {
            const answerId = crypto.randomUUID()
            setCurrentStreamingId(answerId)
            setAnswers(prev => [...prev, {
              id: answerId,
              question: msg.text,
              text: '',
              latencyMs: null,
              isStreaming: true,
            }])
          }
          break
        }

        case 'answer_token': {
          if (!currentStreamingId) break
          setAnswers(prev => prev.map(a =>
            a.id === currentStreamingId
              ? {
                  ...a,
                  text: a.isRevising ? a.text : a.text + msg.token,
                  draftText: a.isRevising ? a.draftText : (a.draftText || '') + msg.token,
                }
              : a
          ))
          break
        }

        case 'answer_metadata': {
          if (!currentStreamingId) break
          setAnswers(prev => prev.map(a =>
            a.id === currentStreamingId
              ? {
                  ...a,
                  questionType: msg.question_type,
                  confidence: msg.confidence,
                  starScores: msg.star_scores,
                  hallucinationRisk: msg.hallucination_risk,
                  isCached: msg.is_cached,
                  memoryContext: msg.memory_context ?? a.memoryContext,
                }
              : a
          ))
          break
        }

        case 'revision_token': {
          if (!currentStreamingId) break
          setAnswers(prev => prev.map(a =>
            a.id === currentStreamingId
              ? {
                  ...a,
                  isRevising: true,
                  isRevised: true,
                  activeTab: 'revised',
                  revisedText: (a.revisedText || '') + msg.token,
                  text: (a.revisedText || '') + msg.token,
                }
              : a
          ))
          break
        }

        case 'revision_complete': {
          if (!currentStreamingId) break
          setAnswers(prev => prev.map(a =>
            a.id === currentStreamingId
              ? { ...a, isRevising: false }
              : a
          ))
          break
        }

        case 'answer_complete': {
          setAnswers(prev => prev.map(a =>
            a.id === currentStreamingId
              ? {
                  ...a,
                  latencyMs: msg.latency_ms,
                  isStreaming: false,
                  isRevising: false,
                  draftText: msg.draft_text || a.draftText || a.text,
                  isRevised: msg.is_revised ?? a.isRevised,
                  activeTab: (msg.is_revised || a.isRevised) ? 'revised' : undefined,
                  memoryContext: msg.memory_context ?? a.memoryContext,
                }
              : a
          ))
          setLastLatency(msg.latency_ms)
          setCurrentStreamingId(null)
          break
        }

        case 'speech_telemetry': {
          setSpeechTelemetry({
            wpm: msg.wpm,
            pacingStatus: msg.pacing_status,
            fillerCount: msg.filler_count,
            fillerRate: msg.filler_rate,
          })
          break
        }

        case 'cheat_sheet': {
          setAnswers(prev => {
            if (prev.length === 0) return prev
            const last = prev[prev.length - 1]
            return [
              ...prev.slice(0, -1),
              { ...last, cheatSheet: msg.bullets }
            ]
          })
          break
        }

        case 'predicted_followups': {
          setAnswers(prev => {
            if (prev.length === 0) return prev
            const last = prev[prev.length - 1]
            return [
              ...prev.slice(0, -1),
              { ...last, predictedFollowUps: msg.followups }
            ]
          })
          break
        }

        case 'coding_analysis': {
          setLastCodingAnalysis(msg.analysis)
          break
        }
      }
    })
    return unsubscribe
  }, [onMessage, currentStreamingId])

  // Global clipboard paste listener for instant coding screenshots
  useEffect(() => {
    const handlePaste = (e: ClipboardEvent) => {
      const items = e.clipboardData?.items
      if (!items) return
      for (const item of Array.from(items)) {
        if (item.type.indexOf('image') !== -1) {
          const file = item.getAsFile()
          if (!file) continue
          const reader = new FileReader()
          reader.onload = () => {
            if (typeof reader.result === 'string') {
              sendCodingScreenshot(reader.result)
            }
          }
          reader.readAsDataURL(file)
          break
        }
      }
    }
    window.addEventListener('paste', handlePaste)
    return () => window.removeEventListener('paste', handlePaste)
  }, [sendCodingScreenshot])



  // Session timer
  useEffect(() => {
    if (!isRecording) return
    const interval = setInterval(() => {
      setElapsedSeconds(s => s + 1)
    }, 1000)
    return () => clearInterval(interval)
  }, [isRecording])

  const formatTime = (s: number) => {
    const m = Math.floor(s / 60)
    const sec = s % 60
    return `${m}:${sec.toString().padStart(2, '0')}`
  }

  return (
    <div className="h-screen bg-dark-950 flex flex-col overflow-hidden">
      {/* Header */}
      <header className="bg-dark-900 border-b border-dark-800 px-6 py-3.5 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <Link
            to="/"
            className="p-2 rounded-xl bg-dark-800 border border-dark-700 text-gray-400 hover:text-white transition-colors"
            title="Back to Dashboard"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>

          <div className="flex items-center gap-2.5">
            <div
              className={clsx(
                'w-2.5 h-2.5 rounded-full transition-all',
                connected ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.8)]' : 'bg-red-500'
              )}
            />
            <div>
              <h1 className="text-sm font-semibold text-white flex items-center gap-2">
                <span>Live Interview Copilot</span>
                <span className="text-[10px] bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 px-2 py-0.5 rounded-full">
                  Session #{sessionId?.slice(0, 8)}
                </span>
              </h1>
              <p className="text-[11px] text-gray-500">
                {connected ? 'WebSocket Pipeline Connected' : 'Connecting WebSocket...'}
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-dark-800 border border-dark-700 text-gray-300 text-xs font-mono">
            <Clock className="w-3.5 h-3.5 text-indigo-400" />
            <span>{formatTime(elapsedSeconds)}</span>
          </div>

          {/* Live Telemetry HUD Bar */}
          {speechTelemetry.wpm > 0 && (
            <div
              className={clsx(
                'hidden md:flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs font-medium transition-all',
                speechTelemetry.pacingStatus === 'optimal'
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                  : speechTelemetry.pacingStatus === 'fast'
                  ? 'bg-amber-500/10 border-amber-500/30 text-amber-300'
                  : 'bg-blue-500/10 border-blue-500/30 text-blue-300'
              )}
            >
              <span>Pace: <strong>{speechTelemetry.wpm} WPM</strong> ({speechTelemetry.pacingStatus.toUpperCase()})</span>
            </div>
          )}

          {speechTelemetry.fillerCount > 0 && (
            <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-purple-500/10 border border-purple-500/30 text-purple-300 text-xs">
              <span>Radar: <strong>{speechTelemetry.fillerCount} Fillers</strong> ({speechTelemetry.fillerRate}%)</span>
            </div>
          )}

          {lastLatency && (
            <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-green-500/10 border border-green-500/30 text-green-300 text-xs">
              <Zap className="w-3.5 h-3.5 text-green-400" />
              <span>Response Latency: <strong>{lastLatency}ms</strong></span>
            </div>
          )}

          <input
            type="file"
            accept="image/*"
            ref={fileInputRef}
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (!file) return
              const reader = new FileReader()
              reader.onload = () => {
                if (typeof reader.result === 'string') {
                  sendCodingScreenshot(reader.result)
                }
              }
              reader.readAsDataURL(file)
            }}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={!connected}
            title="Upload coding problem screenshot or paste (Ctrl+V)"
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-dark-800 hover:bg-dark-750 border border-indigo-500/30 text-indigo-300 transition-all shadow-sm disabled:opacity-40"
          >
            <Code className="w-4 h-4 text-indigo-400" />
            <span>Code Screenshot</span>
          </button>



          <button
            onClick={toggleAutoOCR}
            disabled={!connected}
            title="Automatically detect screen visual changes and run OCR without hotkeys"
            className={clsx(
              'flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold transition-all shadow-sm border',
              isAutoOCR
                ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300 animate-pulse'
                : 'bg-dark-800 hover:bg-dark-750 border-indigo-500/30 text-indigo-300 disabled:opacity-40'
            )}
          >
            <Eye className="w-4 h-4 text-emerald-400" />
            <span>{isAutoOCR ? '⚡ Auto OCR: Active' : '⚡ Auto OCR: Off'}</span>
          </button>

          {!isRecording && (
            <button
              onClick={() => setEnableLoopback(!enableLoopback)}
              title="Capture system speaker audio (interviewer voice) alongside your microphone"
              className={clsx(
                'flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold transition-all border',
                enableLoopback
                  ? 'bg-purple-500/20 border-purple-500/40 text-purple-300'
                  : 'bg-dark-800 border-dark-700 text-gray-400 hover:text-gray-300'
              )}
            >
              <Headphones className="w-4 h-4" />
              <span>{enableLoopback ? '🎧 System + Mic Audio' : '🎙️ Mic Only'}</span>
            </button>
          )}

          <button
            onClick={isRecording ? stop : () => start(enableLoopback)}
            disabled={!connected}
            className={clsx(
              'flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all shadow-lg',
              isRecording
                ? 'bg-red-600 hover:bg-red-500 text-white shadow-red-600/25 animate-pulse'
                : 'bg-gradient-to-r from-indigo-600 to-accent-cyan hover:opacity-95 text-white shadow-indigo-600/25 disabled:opacity-40'
            )}
          >
            {isRecording ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
            {isRecording ? 'Stop Recording' : 'Start Recording'}
          </button>
        </div>
      </header>

      {/* PiP View Mode Switcher (Sleek tab bar when in compact window) */}
      <div className="bg-dark-900 border-b border-dark-800 px-4 py-2 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-1.5 bg-dark-950 p-1 rounded-xl border border-dark-800">
          <button
            onClick={() => setPipTab('answers')}
            className={clsx(
              'flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all',
              pipTab === 'answers'
                ? 'bg-gradient-to-r from-indigo-600 to-accent-cyan text-white shadow-sm'
                : 'text-gray-400 hover:text-gray-200'
            )}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>AI Answers ({answers.length})</span>
          </button>
          <button
            onClick={() => setPipTab('transcript')}
            className={clsx(
              'flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all',
              pipTab === 'transcript'
                ? 'bg-gradient-to-r from-indigo-600 to-accent-cyan text-white shadow-sm'
                : 'text-gray-400 hover:text-gray-200'
            )}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Live Transcript ({transcript.length})</span>
          </button>
          <button
            onClick={() => setPipTab('both')}
            className={clsx(
              'flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all',
              pipTab === 'both'
                ? 'bg-gradient-to-r from-indigo-600 to-accent-cyan text-white shadow-sm'
                : 'text-gray-400 hover:text-gray-200'
            )}
          >
            <Monitor className="w-3.5 h-3.5" />
            <span>Split View</span>
          </button>
        </div>
        <span className="text-[11px] text-gray-500 hidden sm:inline">PiP Compact Mode Compatible</span>
      </div>

      {/* Split Screen Workspace */}
      <main className="flex-1 grid grid-cols-1 lg:grid-cols-2 overflow-hidden">
        {/* Left: Diarized Live Transcript */}
        {(pipTab === 'transcript' || pipTab === 'both') && (
          <div className={clsx(
            'flex flex-col border-r border-dark-800 overflow-hidden bg-dark-950/60',
            pipTab === 'transcript' ? 'col-span-1 lg:col-span-2' : 'col-span-1'
          )}>
            <div className="px-5 py-3.5 bg-dark-900/80 border-b border-dark-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-indigo-500" />
              <p className="text-xs font-semibold text-gray-300 uppercase tracking-widest">
                Real-Time Diarized Transcript
              </p>
            </div>
            <span className="text-[11px] text-gray-500">Auto-detecting Interviewer vs. Candidate</span>
          </div>

          <div className="flex-1 overflow-y-auto p-5 space-y-3.5">
            {transcript.map(entry => {
              const role = entry.isQuestion ? 'Interviewer' : (entry.speaker === '1' ? 'Candidate (You)' : 'Interviewer')
              return (
              <div
                key={entry.id}
                className={clsx(
                  'rounded-2xl p-4 border transition-all',
                  entry.isQuestion
                    ? 'border-amber-500/50 bg-amber-500/10 text-amber-100 shadow-md shadow-amber-500/5'
                    : role === 'Interviewer'
                    ? 'border-indigo-500/30 bg-indigo-500/10 text-gray-200'
                    : 'border-dark-700 bg-dark-850/60 text-gray-300'
                )}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <button
                    onClick={() => {
                      setTranscript(prev => prev.map(t => t.id === entry.id ? { ...t, speaker: t.speaker === '0' ? '1' : '0' } : t))
                    }}
                    title="Click to swap Interviewer / Candidate label"
                    className={clsx(
                      'text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded cursor-pointer hover:opacity-80 transition-opacity',
                      entry.isQuestion
                        ? 'bg-amber-400/20 text-amber-300'
                        : role === 'Interviewer'
                        ? 'bg-indigo-400/20 text-indigo-300'
                        : 'bg-gray-700/40 text-gray-400'
                    )}
                  >
                    {entry.isQuestion
                      ? '🎯 Question Detected (Interviewer)'
                      : role}
                  </button>
                  <span className="text-[10px] text-gray-500 font-mono">
                    {new Date(entry.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <p className={clsx('text-sm leading-relaxed', entry.isPartial && 'italic text-gray-400 animate-pulse')}>{entry.text}</p>
              </div>
            )})}

            {transcript.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center text-center p-8">
                <div className="w-12 h-12 rounded-2xl bg-dark-850 border border-dark-700 flex items-center justify-center text-gray-500 mb-3">
                  <Mic className="w-6 h-6" />
                </div>
                <p className="text-sm font-semibold text-gray-300">Awaiting Voice Activity</p>
                <p className="text-xs text-gray-500 mt-1 max-w-sm leading-relaxed">
                  Click &quot;Start Recording&quot; above and speak into your microphone. Our Silero VAD will segment utterances and detect questions automatically.
                </p>
              </div>
            )}
          </div>
        </div>
        )}

        {/* Right: AI Suggested Answers Copilot */}
        {(pipTab === 'answers' || pipTab === 'both') && (
          <div className={clsx(
            'flex flex-col overflow-hidden bg-dark-900/30',
            pipTab === 'answers' ? 'col-span-1 lg:col-span-2' : 'col-span-1'
          )}>
            <div className="px-5 py-3.5 bg-dark-900/80 border-b border-dark-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-accent-cyan" />
              <p className="text-xs font-semibold text-gray-300 uppercase tracking-widest">
                AI Suggested Answer Copilot (STAR Format)
              </p>
            </div>
            <span className="text-[11px] text-accent-cyan font-medium">Groq LLM Llama-3 Streaming</span>
          </div>

          <div className="flex-1 overflow-y-auto p-5 space-y-4">
            {lastCodingAnalysis && (
              <CodingOverlay
                analysis={lastCodingAnalysis}
                onClose={() => setLastCodingAnalysis(null)}
              />
            )}

            {answers.map(answer => {
              const showRevised = answer.activeTab === 'revised' || (!answer.activeTab && (answer.isRevised || Boolean(answer.revisedText)))
              const displayText = showRevised
                ? (answer.revisedText || answer.text)
                : (answer.draftText || answer.text)

              return (
                <div
                  key={answer.id}
                  className="bg-dark-900/80 border border-dark-700/80 rounded-2xl p-5 shadow-xl transition-all hover:border-indigo-500/40"
                >
                  {/* Top Badges Row */}
                  <div className="flex flex-wrap items-center justify-between gap-2 pb-3 mb-3 border-b border-dark-800">
                    <div className="flex items-center gap-2">
                      <ChevronRight className="w-4 h-4 text-accent-cyan mt-0.5 shrink-0" />
                      <div>
                        <span className="text-[10px] font-bold text-accent-cyan uppercase tracking-wider block">
                          Target Question
                        </span>
                        <p className="text-xs font-medium text-gray-200 mt-0.5">{answer.question}</p>
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-1.5">
                      {answer.questionType && (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 uppercase">
                          {answer.questionType.replace('_', ' ')}
                        </span>
                      )}
                      {answer.isCached && (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1">
                          <Zap className="w-3 h-3" />
                          <span>Cached (&lt;10ms)</span>
                        </span>
                      )}
                      {answer.memoryContext?.recalled_count && answer.memoryContext.recalled_count > 0 ? (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-purple-500/20 text-purple-300 border border-purple-500/30 flex items-center gap-1">
                          <Brain className="w-3 h-3" />
                          <span>Recalled {answer.memoryContext.recalled_count} past Q&amp;A</span>
                        </span>
                      ) : null}
                      {answer.memoryContext?.projects_avoided && answer.memoryContext.projects_avoided.length > 0 ? (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-teal-500/20 text-teal-300 border border-teal-500/30">
                          🚫 Avoided repeat: {answer.memoryContext.projects_avoided.slice(0, 2).join(', ')}
                        </span>
                      ) : null}
                    </div>
                  </div>

                  {/* Glanceable Cheat-Sheet Box (<150ms) */}
                  {answer.cheatSheet && answer.cheatSheet.length > 0 && (
                    <div className="mb-3.5 p-3.5 rounded-xl bg-gradient-to-r from-indigo-950/60 to-dark-900 border border-indigo-500/30">
                      <div className="flex items-center gap-1.5 mb-2 text-indigo-300 text-xs font-bold uppercase tracking-wider">
                        <Sparkles className="w-3.5 h-3.5 text-accent-cyan" />
                        <span>Glanceable Key Talking Points (&lt;150ms)</span>
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                        {answer.cheatSheet.map((bullet, idx) => (
                          <div
                            key={idx}
                            className="bg-dark-900/90 border border-indigo-500/20 rounded-lg px-3 py-2 text-xs font-medium text-indigo-100 shadow-sm"
                          >
                            {bullet}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Tab Switcher for BOTH Draft and Revised Answer */}
                  {(answer.isRevised || Boolean(answer.revisedText)) && (
                    <div className="flex items-center gap-2 mb-3 bg-dark-950/60 p-1 rounded-xl border border-dark-800">
                      <button
                        onClick={() => {
                          setAnswers(prev => prev.map(a => a.id === answer.id ? { ...a, activeTab: 'revised' } : a))
                        }}
                        className={clsx(
                          'flex-1 py-1.5 px-3 rounded-lg text-xs font-medium transition-all flex items-center justify-center gap-1.5',
                          showRevised
                            ? 'bg-indigo-600/30 text-indigo-200 border border-indigo-500/40 shadow'
                            : 'text-gray-400 hover:text-gray-200'
                        )}
                      >
                        <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                        <span>✨ Revised &amp; Grounded</span>
                      </button>
                      <button
                        onClick={() => {
                          setAnswers(prev => prev.map(a => a.id === answer.id ? { ...a, activeTab: 'draft' } : a))
                        }}
                        className={clsx(
                          'flex-1 py-1.5 px-3 rounded-lg text-xs font-medium transition-all flex items-center justify-center gap-1.5',
                          !showRevised
                            ? 'bg-dark-800 text-gray-200 border border-dark-700 shadow'
                            : 'text-gray-400 hover:text-gray-200'
                        )}
                      >
                        <Layers className="w-3.5 h-3.5" />
                        <span>📝 Original Draft</span>
                      </button>
                    </div>
                  )}

                  {/* Answer Content */}
                  <div className="text-gray-100 text-sm leading-relaxed space-y-2">
                    <p>
                      {displayText}
                      {(answer.isStreaming || answer.isRevising) && (
                        <span className="inline-block w-1.5 h-4 bg-accent-cyan ml-1 animate-pulse rounded-sm align-middle" />
                      )}
                    </p>
                  </div>

                  {/* STAR Completeness Chips for Behavioral Questions */}
                  {answer.starScores && answer.questionType === 'behavioral' && (
                    <div className="mt-4 pt-3 border-t border-dark-800/80 flex flex-wrap items-center gap-2 text-[10px]">
                      <span className="text-gray-500 uppercase tracking-wider font-semibold">STAR Structure:</span>
                      {Object.entries(answer.starScores).map(([key, val]) => (
                        <span
                          key={key}
                          className={clsx(
                            'px-2 py-0.5 rounded-md font-mono capitalize border',
                            val >= 3
                              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                              : 'bg-gray-800 text-gray-300 border-gray-700'
                          )}
                        >
                          {key}: {'★'.repeat(val)}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Footer Bar: Grounding Confidence & Latency */}
                  {answer.latencyMs && (
                    <div className="mt-4 pt-3 border-t border-dark-800 flex items-center justify-between text-[11px] text-gray-500">
                      <span className="flex items-center gap-1.5 text-green-400">
                        <ShieldCheck className="w-3.5 h-3.5" />
                        <span>
                          {answer.confidence
                            ? `${Math.round(answer.confidence * 100)}% Verified Grounding`
                            : 'RAG Context Injected'}
                        </span>
                      </span>
                      <span>
                        Total Latency: <strong className="text-gray-300">{answer.latencyMs}ms</strong>
                      </span>
                    </div>
                  )}

                  {/* Predicted Next Follow-Ups Drawer */}
                  {answer.predictedFollowUps && answer.predictedFollowUps.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-dark-800 flex flex-wrap items-center gap-2">
                      <span className="text-[11px] font-bold text-accent-cyan uppercase tracking-wider flex items-center gap-1">
                        <Layers className="w-3.5 h-3.5" />
                        <span>Predicted Next Questions (Pre-Cached):</span>
                      </span>
                      {answer.predictedFollowUps.map((fu, idx) => (
                        <span
                          key={idx}
                          className="px-2.5 py-1 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-medium hover:bg-indigo-500/20 transition-colors cursor-default"
                        >
                          {fu}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}

            {answers.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center text-center p-8">
                <div className="w-12 h-12 rounded-2xl bg-dark-850 border border-dark-700 flex items-center justify-center text-accent-cyan mb-3">
                  <Sparkles className="w-6 h-6" />
                </div>
                <p className="text-sm font-semibold text-gray-300">Ready for Interview Questions</p>
                <p className="text-xs text-gray-500 mt-1 max-w-sm leading-relaxed">
                  As soon as an interview question directed at you is detected, your AI copilot will stream a concise STAR-structured answer right here.
                </p>
              </div>
            )}
          </div>
        </div>
        )}
      </main>
    </div>
  )
}
