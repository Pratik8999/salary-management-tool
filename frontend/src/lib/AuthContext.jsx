import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { getMe } from '@/api/auth'
import { clearToken, getToken, setToken } from '@/lib/auth'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [status, setStatus] = useState(() => (getToken() ? 'loading' : 'anonymous'))

  const loadUser = useCallback(async () => {
    if (!getToken()) {
      setUser(null)
      setStatus('anonymous')
      return
    }
    setStatus('loading')
    try {
      const me = await getMe()
      setUser(me)
      setStatus('authenticated')
    } catch {
      clearToken()
      setUser(null)
      setStatus('anonymous')
    }
  }, [])

  useEffect(() => {
    loadUser()
  }, [loadUser])

  const signIn = useCallback(
    async (token) => {
      setToken(token)
      await loadUser()
    },
    [loadUser],
  )

  const signOut = useCallback(() => {
    clearToken()
    setUser(null)
    setStatus('anonymous')
  }, [])

  return (
    <AuthContext.Provider value={{ user, status, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (ctx === null) {
    throw new Error('useAuth must be used inside <AuthProvider>')
  }
  return ctx
}
