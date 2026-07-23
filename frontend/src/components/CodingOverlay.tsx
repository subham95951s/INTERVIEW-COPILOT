import React, { useState } from 'react'
import { CodingProblemAnalysis } from '../hooks/useWebSocket'
import { Code, Clock, Database, AlertCircle, CheckCircle, Terminal, ChevronRight, Sparkles, X } from 'lucide-react'

interface CodingOverlayProps {
  analysis: CodingProblemAnalysis
  onClose?: () => void
}

export const CodingOverlay: React.FC<CodingOverlayProps> = ({ analysis, onClose }) => {
  const [activeTab, setActiveTab] = useState<'approach' | 'pseudocode' | 'solution'>('approach')

  return (
    <div className="bg-gray-950/95 backdrop-blur-xl border border-indigo-500/40 rounded-2xl shadow-2xl p-6 text-sm text-gray-200 transition-all duration-300 relative overflow-hidden">
      {/* Decorative top glow */}
      <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500" />

      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-gray-800 mb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/20 flex items-center justify-center text-indigo-400">
            <Code size={18} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-indigo-400">
                Coding Problem Analysis
              </span>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-indigo-950 border border-indigo-800 text-indigo-300">
                <Sparkles size={10} /> AI Structured
              </span>
            </div>
            <h3 className="text-base font-semibold text-white mt-0.5">
              {analysis.problem_summary || 'Extracted Algorithm Problem'}
            </h3>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Complexity Chips */}
          <div className="flex items-center gap-2 bg-gray-900/80 border border-gray-800 px-3 py-1.5 rounded-xl">
            <div className="flex items-center gap-1 text-xs text-yellow-400 font-mono">
              <Clock size={13} className="text-yellow-500" />
              <span>{analysis.time_complexity || 'O(N)'}</span>
            </div>
            <span className="text-gray-700">|</span>
            <div className="flex items-center gap-1 text-xs text-amber-400 font-mono">
              <Database size={13} className="text-amber-500" />
              <span>{analysis.space_complexity || 'O(1)'}</span>
            </div>
          </div>

          {onClose && (
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white p-1.5 rounded-lg hover:bg-gray-800/80 transition-colors"
              title="Close overlay"
            >
              <X size={18} />
            </button>
          )}
        </div>
      </div>

      {/* Tab Switcher */}
      <div className="flex items-center gap-2 mb-5 bg-gray-900/90 p-1 rounded-xl border border-gray-800/80">
        <button
          onClick={() => setActiveTab('approach')}
          className={`flex-1 py-2 px-3 rounded-lg text-xs font-medium flex items-center justify-center gap-1.5 transition-all ${
            activeTab === 'approach'
              ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30'
              : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
          }`}
        >
          <Sparkles size={14} /> Optimal Approach & Logic
        </button>
        <button
          onClick={() => setActiveTab('pseudocode')}
          className={`flex-1 py-2 px-3 rounded-lg text-xs font-medium flex items-center justify-center gap-1.5 transition-all ${
            activeTab === 'pseudocode'
              ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-600/30'
              : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
          }`}
        >
          <Terminal size={14} /> Pseudocode Breakdown
        </button>
        <button
          onClick={() => setActiveTab('solution')}
          className={`flex-1 py-2 px-3 rounded-lg text-xs font-medium flex items-center justify-center gap-1.5 transition-all ${
            activeTab === 'solution'
              ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/30'
              : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
          }`}
        >
          <Code size={14} /> Full Python Solution
          {!analysis.solution_code_python && (
            <span className="w-2 h-2 rounded-full bg-yellow-400 animate-ping ml-1" />
          )}
        </button>
      </div>

      {/* Tab Content */}
      <div className="space-y-4 max-h-[420px] overflow-y-auto pr-1">
        {activeTab === 'approach' && (
          <div className="space-y-4">
            {/* Approach explanation */}
            <div className="bg-gray-900/60 rounded-xl p-4 border border-gray-800/60">
              <h4 className="text-xs font-semibold text-indigo-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <ChevronRight size={14} /> Strategic Approach (Verbal Explanation)
              </h4>
              <p className="text-gray-300 leading-relaxed whitespace-pre-wrap text-sm">
                {analysis.approach || 'Reviewing problem specifics...'}
              </p>
            </div>

            {/* Input / Output & Constraints */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {(analysis.input_format || analysis.output_format) && (
                <div className="bg-gray-900/50 rounded-xl p-3.5 border border-gray-800/50 space-y-2">
                  {analysis.input_format && (
                    <div>
                      <span className="text-xs text-gray-400 block font-medium">Input Format:</span>
                      <span className="text-xs font-mono text-gray-200">{analysis.input_format}</span>
                    </div>
                  )}
                  {analysis.output_format && (
                    <div>
                      <span className="text-xs text-gray-400 block font-medium">Output Format:</span>
                      <span className="text-xs font-mono text-gray-200">{analysis.output_format}</span>
                    </div>
                  )}
                </div>
              )}

              {analysis.constraints && analysis.constraints.length > 0 && (
                <div className="bg-gray-900/50 rounded-xl p-3.5 border border-gray-800/50">
                  <span className="text-xs text-gray-400 block font-medium mb-1.5">Constraints & Bounds:</span>
                  <ul className="space-y-1">
                    {analysis.constraints.map((c, idx) => (
                      <li key={idx} className="text-xs font-mono text-indigo-300 flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-indigo-500" /> {c}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Edge Cases */}
            {analysis.edge_cases && analysis.edge_cases.length > 0 && (
              <div className="bg-amber-950/20 border border-amber-500/30 rounded-xl p-3.5">
                <h5 className="text-xs font-semibold text-amber-400 flex items-center gap-1.5 mb-2">
                  <AlertCircle size={14} /> Critical Edge Cases to Mention First
                </h5>
                <div className="flex flex-wrap gap-2">
                  {analysis.edge_cases.map((ec, idx) => (
                    <span
                      key={idx}
                      className="px-2.5 py-1 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-200 text-xs font-medium"
                    >
                      • {ec}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'pseudocode' && (
          <div className="space-y-3">
            <div className="bg-gray-900 rounded-xl p-4 border border-emerald-500/30 font-mono text-xs overflow-x-auto">
              <div className="flex items-center justify-between text-emerald-400 text-[11px] uppercase tracking-wider mb-2.5 pb-2 border-b border-gray-800">
                <span>Step-by-Step Pseudocode</span>
                <span>Language-Agnostic Logic</span>
              </div>
              <pre className="text-emerald-300 leading-relaxed whitespace-pre-wrap">
                {analysis.pseudocode || '// Extracting pseudocode steps...'}
              </pre>
            </div>

            {analysis.follow_up_considerations && analysis.follow_up_considerations.length > 0 && (
              <div className="bg-gray-900/60 rounded-xl p-3.5 border border-gray-800">
                <h5 className="text-xs font-semibold text-indigo-300 flex items-center gap-1.5 mb-2">
                  <CheckCircle size={14} /> Potential Follow-Up Questions to Anticipate
                </h5>
                <ul className="space-y-1 text-xs text-gray-300">
                  {analysis.follow_up_considerations.map((fu, idx) => (
                    <li key={idx} className="flex items-start gap-1.5">
                      <span className="text-indigo-400 mt-0.5">→</span> {fu}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {activeTab === 'solution' && (
          <div className="space-y-3">
            {analysis.solution_code_python ? (
              <div className="bg-gray-900 rounded-xl p-4 border border-purple-500/30 font-mono text-xs overflow-x-auto">
                <div className="flex items-center justify-between text-purple-400 text-[11px] uppercase tracking-wider mb-2.5 pb-2 border-b border-gray-800">
                  <span>Complete Python Solution</span>
                  <span>Optimized & Edge-Case Ready</span>
                </div>
                <pre className="text-purple-200 leading-relaxed whitespace-pre">
                  {analysis.solution_code_python}
                </pre>
              </div>
            ) : (
              <div className="bg-gray-900/80 rounded-xl p-8 border border-purple-500/20 flex flex-col items-center justify-center text-center">
                <div className="w-8 h-8 rounded-full border-2 border-purple-500 border-t-transparent animate-spin mb-3" />
                <p className="text-sm font-medium text-purple-300">Generating Optimized Python Solution...</p>
                <p className="text-xs text-gray-400 mt-1">Our LLM is writing clean code based on the verified approach.</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
