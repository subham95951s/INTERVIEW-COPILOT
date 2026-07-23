import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'

export interface UserProfile {
  user_id: string
  email: string
  name: string
  credits: number
}

interface AuthContextType {
  token: string | null
  user: UserProfile | null
  login: (token: string, user: UserProfile) => void
  logout: () => void
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('ic_access_token'))
  const [user, setUser] = useState<UserProfile | null>(() => {
    const saved = localStorage.getItem('ic_user')
    return saved ? JSON.parse(saved) : null
  })

  useEffect(() => {
    if (token && !user) {
      // Fetch user profile if token exists
      fetch('http://localhost:8000/auth/me', {
        headers: { Authorization: `Bearer ${token}` }
      })
        .then(res => res.ok ? res.json() : Promise.reject())
        .then(data => {
          const profile: UserProfile = {
            user_id: data.user_id,
            email: data.email,
            name: data.name || data.email.split('@')[0],
            credits: data.credits
          }
          setUser(profile)
          localStorage.setItem('ic_user', JSON.stringify(profile))
        })
        .catch(() => {
          localStorage.removeItem('ic_access_token')
          localStorage.removeItem('ic_user')
          setToken(null)
          setUser(null)
        })
    }
  }, [token, user])

  const login = (newToken: string, newUser: UserProfile) => {
    localStorage.setItem('ic_access_token', newToken)
    localStorage.setItem('ic_user', JSON.stringify(newUser))
    setToken(newToken)
    setUser(newUser)
  }

  const logout = () => {
    localStorage.removeItem('ic_access_token')
    localStorage.removeItem('ic_user')
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ token, user, login, logout, isAuthenticated: !!token }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
