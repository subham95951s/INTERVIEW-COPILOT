import { useEffect, useRef, useCallback, useState } from 'react'

export interface MemoryContextData {
  recalled_count?: number
  projects_avoided?: string[]
}

export interface CodingProblemAnalysis {
  problem_summary: string
  input_format: string
  output_format: string
  constraints: string[]
  examples: { input: string; output: string; explanation?: string }[]
  approach: string
  pseudocode: string
  time_complexity: string
  space_complexity: string
  edge_cases: string[]
  follow_up_considerations: string[]
  solution_code_python: string | null
}

export type WSMessage =
  | { type: 'transcript_partial'; speaker: string; text: string }
  | { type: 'transcript_final'; speaker: string; text: string; is_question: boolean }
  | { type: 'answer_token'; token: string }
  | { type: 'answer_metadata'; question_type: string; confidence: number; star_scores: Record<string, number>; hallucination_risk: string; is_cached?: boolean; memory_context?: MemoryContextData }
  | { type: 'revision_token'; token: string }
  | { type: 'revision_complete' }
  | { type: 'answer_complete'; full_text: string; draft_text?: string; is_revised?: boolean; latency_ms: number; memory_context?: MemoryContextData }
  | { type: 'speech_telemetry'; wpm: number; pacing_status: 'optimal' | 'fast' | 'slow'; filler_count: number; filler_rate: number; total_words: number }
  | { type: 'cheat_sheet'; bullets: string[] }
  | { type: 'predicted_followups'; followups: string[] }
  | { type: 'coding_analysis'; analysis: CodingProblemAnalysis }
  | { type: 'error'; message: string }

type MessageHandler = (msg: WSMessage) => void

export function useWebSocket(sessionId: string | null, token: string | null = null) {
  const ws = useRef<WebSocket | null>(null)
  const handlers = useRef<Set<MessageHandler>>(new Set())
  const [connected, setConnected] = useState(false)

  const connect = useCallback(() => {
    if (!sessionId || ws.current?.readyState === WebSocket.OPEN) return

    const authToken = token || localStorage.getItem('token') || ''
    const url = `ws://localhost:8000/ws/session/${sessionId}${authToken ? `?token=${encodeURIComponent(authToken)}` : ''}`
    ws.current = new WebSocket(url)

    ws.current.onopen = () => {
      setConnected(true)
      console.log('[WS] Connected:', sessionId)
    }

    ws.current.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data) as WSMessage
        handlers.current.forEach(h => h(msg))
      } catch (e) {
        console.error('[WS] Parse error:', e)
      }
    }

    ws.current.onclose = () => {
      setConnected(false)
      console.log('[WS] Disconnected')
    }

    ws.current.onerror = (err) => {
      console.error('[WS] Error:', err)
    }
  }, [sessionId, token])

  const disconnect = useCallback(() => {
    ws.current?.close()
    ws.current = null
    setConnected(false)
  }, [])

  const sendBinary = useCallback((data: ArrayBuffer) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(data)
    }
  }, [])

  const sendJSON = useCallback((data: object) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data))
    }
  }, [])

  const sendCodingScreenshot = useCallback((imageBase64: string) => {
    sendJSON({ type: 'coding_screenshot', image_base64: imageBase64 })
  }, [sendJSON])

  const onMessage = useCallback((handler: MessageHandler) => {
    handlers.current.add(handler)
    return () => {
      handlers.current.delete(handler)
    }
  }, [])

  useEffect(() => {
    if (sessionId) connect()
    return () => disconnect()
  }, [sessionId, connect, disconnect])

  return { connected, connect, disconnect, sendBinary, sendJSON, sendCodingScreenshot, onMessage }
}
