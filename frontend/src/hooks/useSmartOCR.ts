import { useState, useEffect, useRef, useCallback } from 'react'

interface UseSmartOCROptions {
  onSignificantChange: (base64Image: string) => void
  intervalMs?: number
  hammingThreshold?: number
}

export function useSmartOCR({
  onSignificantChange,
  intervalMs = 2500,
  hammingThreshold = 12
}: UseSmartOCROptions) {
  const [isEnabled, setIsEnabled] = useState(false)
  const [lastCaptureTime, setLastCaptureTime] = useState<number | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [lastHammingDistance, setLastHammingDistance] = useState<number | null>(null)

  const streamRef = useRef<MediaStream | null>(null)
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const smallCanvasRef = useRef<HTMLCanvasElement | null>(null)
  const fullCanvasRef = useRef<HTMLCanvasElement | null>(null)
  const lastHashRef = useRef<string | null>(null)

  // Compute 64-bit difference hash (dHash) from 9x8 grayscale image
  const computeDHash = (ctx: CanvasRenderingContext2D, width: number, height: number): string => {
    const imgData = ctx.getImageData(0, 0, width, height).data
    const grayscale = new Uint8Array(width * height)
    for (let i = 0; i < imgData.length; i += 4) {
      // Luminance formula
      grayscale[i / 4] = Math.round(0.299 * imgData[i] + 0.587 * imgData[i + 1] + 0.114 * imgData[i + 2])
    }

    let hash = ''
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width - 1; x++) {
        const left = grayscale[y * width + x]
        const right = grayscale[y * width + (x + 1)]
        hash += left > right ? '1' : '0'
      }
    }
    return hash
  }

  // Compute Hamming distance between two binary hash strings
  const getHammingDistance = (hash1: string, hash2: string): number => {
    if (hash1.length !== hash2.length) return 64
    let distance = 0
    for (let i = 0; i < hash1.length; i++) {
      if (hash1[i] !== hash2[i]) {
        distance++
      }
    }
    return distance
  }

  const stopCapture = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop())
      streamRef.current = null
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
    setIsEnabled(false)
    lastHashRef.current = null
  }, [])

  const startCapture = useCallback(async () => {
    try {
      if (streamRef.current) {
        stopCapture()
      }

      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: ({
          cursor: 'never',
          frameRate: { max: 5 }
        } as unknown as MediaTrackConstraints),
        audio: false
      })

      streamRef.current = stream

      // Handle user stopping screen share via browser bar
      stream.getVideoTracks()[0].onended = () => {
        stopCapture()
      }

      if (!videoRef.current) {
        videoRef.current = document.createElement('video')
        videoRef.current.autoplay = true
        videoRef.current.muted = true
      }
      videoRef.current.srcObject = stream
      await videoRef.current.play()

      setIsEnabled(true)
    } catch (err) {
      console.warn('[SmartOCR] Screen capture not granted or cancelled:', err)
      setIsEnabled(false)
    }
  }, [stopCapture])

  const toggle = useCallback(() => {
    if (isEnabled) {
      stopCapture()
    } else {
      startCapture()
    }
  }, [isEnabled, startCapture, stopCapture])

  useEffect(() => {
    if (!isEnabled || !streamRef.current || !videoRef.current) return

    if (!smallCanvasRef.current) {
      smallCanvasRef.current = document.createElement('canvas')
      smallCanvasRef.current.width = 9
      smallCanvasRef.current.height = 8
    }
    if (!fullCanvasRef.current) {
      fullCanvasRef.current = document.createElement('canvas')
    }

    const interval = setInterval(() => {
      if (isProcessing) return
      const video = videoRef.current
      const smallCanvas = smallCanvasRef.current
      const fullCanvas = fullCanvasRef.current
      if (!video || !smallCanvas || !fullCanvas || video.videoWidth === 0) return

      const smallCtx = smallCanvas.getContext('2d', { willReadFrequently: true })
      if (!smallCtx) return

      // Draw 9x8 for fast dHash computation
      smallCtx.drawImage(video, 0, 0, 9, 8)
      const currentHash = computeDHash(smallCtx, 9, 8)

      let distance = 64
      if (lastHashRef.current) {
        distance = getHammingDistance(lastHashRef.current, currentHash)
        setLastHammingDistance(distance)
      } else {
        lastHashRef.current = currentHash
        return
      }

      // If visual change exceeds threshold, capture full high-res and trigger OCR
      if (distance >= hammingThreshold) {
        lastHashRef.current = currentHash
        setIsProcessing(true)

        fullCanvas.width = video.videoWidth
        fullCanvas.height = video.videoHeight
        const fullCtx = fullCanvas.getContext('2d')
        if (fullCtx) {
          fullCtx.drawImage(video, 0, 0, fullCanvas.width, fullCanvas.height)
          const base64 = fullCanvas.toDataURL('image/jpeg', 0.85)
          setLastCaptureTime(Date.now())
          onSignificantChange(base64)
        }
        setIsProcessing(false)
      }
    }, intervalMs)

    return () => clearInterval(interval)
  }, [isEnabled, isProcessing, intervalMs, hammingThreshold, onSignificantChange])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopCapture()
    }
  }, [stopCapture])

  return {
    isEnabled,
    toggle,
    lastCaptureTime,
    lastHammingDistance,
    isProcessing
  }
}
