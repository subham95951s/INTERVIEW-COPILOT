import { useRef, useCallback, useState } from 'react'

const SAMPLE_RATE = 16000

export function useAudioCapture(onPCMChunk: (chunk: ArrayBuffer) => void) {
  const audioContext = useRef<AudioContext | null>(null)
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null)
  const systemSourceRef = useRef<MediaStreamAudioSourceNode | null>(null)
  const processor = useRef<ScriptProcessorNode | null>(null)
  const stream = useRef<MediaStream | null>(null)
  const systemStream = useRef<MediaStream | null>(null)
  const [isRecording, setIsRecording] = useState(false)
  const [isLoopbackActive, setIsLoopbackActive] = useState(false)

  const start = useCallback(async (enableSystemLoopback: boolean = false) => {
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: SAMPLE_RATE,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        }
      })

      if (enableSystemLoopback) {
        try {
          // Request desktop audio loopback (interviewer voice)
          systemStream.current = await navigator.mediaDevices.getDisplayMedia({
            video: true, // Many browsers require video: true to prompt for audio share
            audio: {
              sampleRate: SAMPLE_RATE,
              echoCancellation: false,
              noiseSuppression: false,
            }
          })
          // Immediately stop video tracks so only system audio is captured without screen recording overhead
          systemStream.current.getVideoTracks().forEach(t => t.stop())
          setIsLoopbackActive(true)
        } catch (sysErr) {
          console.warn('[Audio] System audio loopback not granted or cancelled, continuing with mic only:', sysErr)
          setIsLoopbackActive(false)
        }
      } else {
        setIsLoopbackActive(false)
      }

      audioContext.current = new AudioContext({ sampleRate: SAMPLE_RATE })
      if (audioContext.current.state === 'suspended') {
        await audioContext.current.resume()
      }
      sourceRef.current = audioContext.current.createMediaStreamSource(stream.current)

      // ScriptProcessor for simplicity (AudioWorklet for production)
      processor.current = audioContext.current.createScriptProcessor(4096, 1, 1)

      sourceRef.current.connect(processor.current)

      // Connect system audio source to the same processor node to sum/mix both channels
      if (systemStream.current && systemStream.current.getAudioTracks().length > 0) {
        systemSourceRef.current = audioContext.current.createMediaStreamSource(systemStream.current)
        systemSourceRef.current.connect(processor.current)
      }

      processor.current.onaudioprocess = (e: AudioProcessingEvent) => {
        const rawFloat32 = e.inputBuffer.getChannelData(0)
        const actualSampleRate = audioContext.current?.sampleRate || SAMPLE_RATE

        let float32: Float32Array
        if (actualSampleRate === SAMPLE_RATE) {
          float32 = rawFloat32
        } else {
          // Linear interpolation downsampling to prevent aliasing
          const ratio = actualSampleRate / SAMPLE_RATE
          const newLength = Math.floor(rawFloat32.length / ratio)
          float32 = new Float32Array(newLength)
          for (let i = 0; i < newLength; i++) {
            const pos = i * ratio
            const idx = Math.floor(pos)
            const frac = pos - idx
            const s0 = rawFloat32[idx] || 0
            const s1 = rawFloat32[idx + 1] || s0
            float32[i] = s0 * (1 - frac) + s1 * frac
          }
        }

        const int16 = new Int16Array(float32.length)
        for (let i = 0; i < float32.length; i++) {
          const clamped = Math.max(-1, Math.min(1, float32[i]))
          int16[i] = clamped < 0 ? clamped * 32768 : clamped * 32767
        }

        onPCMChunk(int16.buffer)
      }

      // Mute direct playback to speakers to prevent audio feedback loop
      const muteGain = audioContext.current.createGain()
      muteGain.gain.value = 0
      processor.current.connect(muteGain)
      muteGain.connect(audioContext.current.destination)
      setIsRecording(true)

    } catch (err) {
      console.error('[Audio] Failed to start capture:', err)
      throw err
    }
  }, [onPCMChunk])

  const stop = useCallback(() => {
    processor.current?.disconnect()
    processor.current = null
    sourceRef.current?.disconnect()
    sourceRef.current = null
    systemSourceRef.current?.disconnect()
    systemSourceRef.current = null
    audioContext.current?.close()
    audioContext.current = null
    stream.current?.getTracks().forEach(t => t.stop())
    stream.current = null
    systemStream.current?.getTracks().forEach(t => t.stop())
    systemStream.current = null
    setIsRecording(false)
    setIsLoopbackActive(false)
  }, [])

  return { isRecording, isLoopbackActive, start, stop }
}
