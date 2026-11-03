import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { apiRequest } from '../lib/api'

const STORAGE_KEY = 'niceday_session'
const AuthContext = createContext(null)

function readStoredSession() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null')
  } catch {
    return null
  }
}

export function AuthProvider({ children }) {
  const [session, setSession] = useState(readStoredSession)

  const signOut = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY)
    setSession(null)
  }, [])

  const saveSession = useCallback((next) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    setSession(next)
  }, [])

  const signIn = useCallback(
    (next) => {
      if (!next?.token || !next?.user) {
        throw new Error('The server did not return a valid session. Please try again.')
      }
      saveSession({ token: next.token, user: next.user })
    },
    [saveSession],
  )

  const updateToken = useCallback(
    (token) => {
      setSession((current) => {
        if (!current) return current
        const next = { ...current, token }
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
        return next
      })
    },
    [],
  )

  useEffect(() => {
    if (!session?.token) return undefined
    let active = true
    apiRequest('/auth/me', { token: session.token })
      .then((result) => {
        if (!active) return
        const nextUser = result?.data?.user
        if (!nextUser) {
          localStorage.removeItem(STORAGE_KEY)
          setSession(null)
          return
        }
        const next = { ...session, user: nextUser }
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
        setSession(next)
      })
      .catch((error) => {
        if (active && error.status === 401) {
          localStorage.removeItem(STORAGE_KEY)
          setSession(null)
        }
      })
    return () => {
      active = false
    }
    // Validate the stored token once when the app loads.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const value = useMemo(
    () => ({
      session,
      user: session?.user || null,
      token: session?.token || null,
      signIn,
      signOut,
      updateToken,
    }),
    [session, signIn, signOut, updateToken],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider')
  }
  return context
}
