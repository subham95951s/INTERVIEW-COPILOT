import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Sparkles, Zap, LogOut, User as UserIcon } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import clsx from 'clsx'

export default function Navbar() {
  const { user, logout, isAuthenticated } = useAuth()
  const location = useLocation()

  // Hide Navbar when inside active interview session for maximum screen real estate
  if (location.pathname.startsWith('/interview')) {
    return null
  }

  return (
    <header data-tauri-drag-region className="sticky top-0 z-50 glass-panel border-b border-dark-800 px-6 py-3.5">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-accent-cyan flex items-center justify-center shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <span className="text-lg font-bold bg-gradient-to-r from-white via-gray-200 to-indigo-300 bg-clip-text text-transparent">
              InterviewCopilot
            </span>
            <span className="text-[10px] block text-accent-cyan font-semibold uppercase tracking-widest -mt-1">
              Real-Time AI
            </span>
          </div>
        </Link>

        <nav className="flex items-center gap-6">
          <Link
            to="/"
            className={clsx(
              'text-sm font-medium transition-colors hover:text-white',
              location.pathname === '/' ? 'text-white' : 'text-gray-400'
            )}
          >
            Dashboard
          </Link>

          {isAuthenticated && user ? (
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs font-semibold">
                <Zap className="w-3.5 h-3.5 text-accent-cyan animate-pulse" />
                <span>{user.credits} Free Credits</span>
              </div>

              <div className="flex items-center gap-2 text-sm text-gray-300">
                <div className="w-7 h-7 rounded-full bg-dark-800 border border-dark-700 flex items-center justify-center text-xs font-bold text-indigo-400">
                  <UserIcon className="w-4 h-4" />
                </div>
                <span className="hidden sm:inline">{user.name}</span>
              </div>

              <button
                onClick={logout}
                className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-dark-800 transition-colors"
                title="Logout"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-3">
              <Link
                to="/login"
                className="text-sm font-medium text-gray-300 hover:text-white px-3 py-1.5"
              >
                Log In
              </Link>
              <Link
                to="/signup"
                className="text-sm font-semibold bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white px-4 py-2 rounded-xl shadow-md shadow-indigo-600/20 transition-all hover:shadow-indigo-500/30"
              >
                Get Started
              </Link>
            </div>
          )}
        </nav>
      </div>
    </header>
  )
}
