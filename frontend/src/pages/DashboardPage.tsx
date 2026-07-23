import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  FileText,
  Briefcase,
  Play,
  CheckCircle2,
  AlertCircle,
  Upload,
  Layers,
  Sparkles,
  ArrowRight,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import clsx from 'clsx'

export default function DashboardPage() {
  const { token } = useAuth()
  const navigate = useNavigate()



  // Resume Upload State
  const [resumeFile, setResumeFile] = useState<File | null>(null)
  const [resumeStatus, setResumeStatus] = useState<string | null>(null)
  const [resumeLoading, setResumeLoading] = useState(false)

  // JD Submission State
  const [company, setCompany] = useState('')
  const [role, setRole] = useState('')
  const [jdText, setJdText] = useState('')
  const [jdStatus, setJdStatus] = useState<string | null>(null)
  const [jdLoading, setJdLoading] = useState(false)

  // Session Config State
  const [interviewType, setInterviewType] = useState('behavioral')
  const [mode, setMode] = useState('mock')
  const [sessionLoading, setSessionLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const headers: Record<string, string> = {}
  if (token) headers['Authorization'] = `Bearer ${token}`

  const handleUploadResume = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!resumeFile) return

    setResumeLoading(true)
    setResumeStatus(null)
    setError(null)

    const formData = new FormData()
    formData.append('file', resumeFile)

    try {
      const res = await fetch('http://localhost:8000/resumes/', {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to upload resume')
      }
      setResumeStatus('Resume uploaded & indexed successfully!')
    } catch (err: any) {
      setError(err.message)
    } finally {
      setResumeLoading(false)
    }
  }

  const handleSubmitJD = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!jdText.trim()) return

    setJdLoading(true)
    setJdStatus(null)
    setError(null)

    try {
      const res = await fetch('http://localhost:8000/job-descriptions/', {
        method: 'POST',
        headers: {
          ...headers,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          raw_text: jdText,
          company: company || 'Company',
          role: role || 'Role',
        }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to submit job description')
      }
      setJdStatus('Job description indexed successfully!')
    } catch (err: any) {
      setError(err.message)
    } finally {
      setJdLoading(false)
    }
  }

  const handleStartSession = async () => {
    setSessionLoading(true)
    setError(null)

    try {
      const res = await fetch('http://localhost:8000/sessions/', {
        method: 'POST',
        headers: {
          ...headers,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          mode,
          interview_type: interviewType,
        }),
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to initialize session')
      }

      const data = await res.json()
      navigate(`/interview/${data.id}`)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setSessionLoading(false)
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-10 space-y-10">
      {/* Hero Banner */}
      <div className="relative rounded-3xl bg-gradient-to-r from-dark-900 via-dark-850 to-indigo-950/40 border border-dark-700/60 p-8 sm:p-10 overflow-hidden shadow-2xl">
        <div className="absolute -right-20 -bottom-20 w-80 h-80 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="max-w-2xl relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs font-semibold mb-4">
            <Sparkles className="w-3.5 h-3.5 text-accent-cyan" />
            <span>Real-Time Voice & RAG Copilot</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold text-white tracking-tight">
            Configure Your AI Interview Copilot
          </h1>
          <p className="text-gray-400 mt-2.5 text-sm sm:text-base leading-relaxed">
            Upload your resume and target job description to prime the vector search engine.
            During your interview, our real-time STT pipeline will listen to the interviewer and generate STAR-formatted suggested answers in under 600ms.
          </p>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/30 flex items-center gap-3 text-red-300 text-sm">
          <AlertCircle className="w-5 h-5 shrink-0 text-red-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Grid: 3 steps */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Step 1: Upload Resume */}
        <div className="glass-card p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
                <FileText className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-white">1. Candidate Resume</h2>
                <p className="text-xs text-gray-400">Upload PDF or DOCX file</p>
              </div>
            </div>

            <form onSubmit={handleUploadResume} className="space-y-4">
              <label className="flex flex-col items-center justify-center border-2 border-dashed border-dark-700 hover:border-indigo-500/50 rounded-2xl p-6 cursor-pointer bg-dark-900/40 transition-colors">
                <Upload className="w-6 h-6 text-gray-500 mb-2" />
                <span className="text-xs font-medium text-gray-300 text-center">
                  {resumeFile ? resumeFile.name : 'Click to select PDF or DOCX'}
                </span>
                <span className="text-[10px] text-gray-500 mt-1">Max 10MB</span>
                <input
                  type="file"
                  accept=".pdf,.docx"
                  className="hidden"
                  onChange={e => setResumeFile(e.target.files?.[0] || null)}
                />
              </label>

              {resumeStatus && (
                <div className="p-3 rounded-xl bg-green-500/10 border border-green-500/30 flex items-center gap-2 text-green-300 text-xs">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span>{resumeStatus}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={!resumeFile || resumeLoading}
                className="w-full bg-dark-800 hover:bg-dark-700 disabled:opacity-40 border border-dark-700 text-white font-medium py-2.5 rounded-xl text-sm transition-all"
              >
                {resumeLoading ? 'Indexing Resume...' : 'Upload & Embed Resume'}
              </button>
            </form>
          </div>
        </div>

        {/* Step 2: Job Description */}
        <div className="glass-card p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-accent-cyan/10 border border-accent-cyan/30 flex items-center justify-center text-accent-cyan">
                <Briefcase className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-white">2. Target Job Role</h2>
                <p className="text-xs text-gray-400">Paste job description requirements</p>
              </div>
            </div>

            <form onSubmit={handleSubmitJD} className="space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="text"
                  placeholder="Company"
                  value={company}
                  onChange={e => setCompany(e.target.value)}
                  className="bg-dark-900 border border-dark-700 rounded-xl px-3 py-2 text-xs text-gray-100 placeholder-gray-600 focus:outline-none focus:border-indigo-500"
                />
                <input
                  type="text"
                  placeholder="Role Title"
                  value={role}
                  onChange={e => setRole(e.target.value)}
                  className="bg-dark-900 border border-dark-700 rounded-xl px-3 py-2 text-xs text-gray-100 placeholder-gray-600 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <textarea
                rows={4}
                placeholder="Paste the full job description here..."
                value={jdText}
                onChange={e => setJdText(e.target.value)}
                className="w-full bg-dark-900 border border-dark-700 rounded-xl p-3 text-xs text-gray-100 placeholder-gray-600 focus:outline-none focus:border-indigo-500 resize-none"
              />

              {jdStatus && (
                <div className="p-3 rounded-xl bg-green-500/10 border border-green-500/30 flex items-center gap-2 text-green-300 text-xs">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span>{jdStatus}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={!jdText.trim() || jdLoading}
                className="w-full bg-dark-800 hover:bg-dark-700 disabled:opacity-40 border border-dark-700 text-white font-medium py-2.5 rounded-xl text-sm transition-all"
              >
                {jdLoading ? 'Embedding JD...' : 'Submit Job Description'}
              </button>
            </form>
          </div>
        </div>

        {/* Step 3: Launch Copilot */}
        <div className="glass-card p-6 flex flex-col justify-between bg-gradient-to-b from-dark-850 to-indigo-950/30 border-indigo-500/20">
          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-accent-cyan flex items-center justify-center text-white shadow-lg shadow-indigo-500/20">
                <Play className="w-5 h-5 fill-current" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-white">3. Launch Live Copilot</h2>
                <p className="text-xs text-gray-400">Real-time voice & answer stream</p>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-2">
                  Interview Type
                </label>
                <select
                  value={interviewType}
                  onChange={e => setInterviewType(e.target.value)}
                  className="w-full bg-dark-900 border border-dark-700 rounded-xl px-3.5 py-2.5 text-sm text-gray-100 focus:outline-none focus:border-indigo-500"
                >
                  <option value="behavioral">Behavioral (STAR method focus)</option>
                  <option value="technical">Technical / Coding</option>
                  <option value="system_design">System Design Architecture</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-2">
                  Session Mode
                </label>
                <select
                  value={mode}
                  onChange={e => setMode(e.target.value)}
                  className="w-full bg-dark-900 border border-dark-700 rounded-xl px-3.5 py-2.5 text-sm text-gray-100 focus:outline-none focus:border-indigo-500"
                >
                  <option value="mock">Mock Practice Mode</option>
                  <option value="live">Live Real Interview Assist</option>
                </select>
              </div>
            </div>
          </div>

          <button
            onClick={handleStartSession}
            disabled={sessionLoading}
            className="w-full mt-6 bg-gradient-to-r from-indigo-600 via-indigo-500 to-accent-cyan hover:opacity-95 text-white font-semibold py-3.5 rounded-xl shadow-xl shadow-indigo-600/30 flex items-center justify-center gap-2 transition-all group"
          >
            <span>{sessionLoading ? 'Initializing Session...' : 'Start Real-Time Copilot'}</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </button>
        </div>
      </div>
    </div>
  )
}
