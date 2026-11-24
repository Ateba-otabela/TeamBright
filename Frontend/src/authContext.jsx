import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { apiClient, getApiErrorMessage } from './services/api/client'

const AuthContext = createContext(null)

function saveSession(token, user) {
  localStorage.setItem('camerhits_access_token', token)
  localStorage.setItem('camerhits_user', JSON.stringify(user))
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [connectionError, setConnectionError] = useState('')

  useEffect(() => {
    const token = localStorage.getItem('camerhits_access_token')
    if (!token) {
      setLoading(false)
      return
    }

    let active = true
    apiClient.get('/me')
      .then(({ data }) => { if (active) setUser(data) })
      .catch((error) => {
        if (!active) return
        if (error.response?.status === 401) {
          localStorage.removeItem('camerhits_access_token')
          localStorage.removeItem('camerhits_user')
          setUser(null)
        } else {
          setConnectionError(getApiErrorMessage(error))
        }
      })
      .finally(() => { if (active) setLoading(false) })

    return () => { active = false }
  }, [])

  const login = useCallback(async (phone, pin) => {
    setConnectionError('')
    const { data } = await apiClient.post('/auth/login', { phone, pin })
    saveSession(data.access_token, data.user)
    try {
      const currentUser = await apiClient.get('/me')
      setUser(currentUser.data)
    } catch (error) {
      localStorage.removeItem('camerhits_access_token')
      localStorage.removeItem('camerhits_user')
      throw error
    }
  }, [])

  const register = useCallback(async (details) => {
    await apiClient.post('/auth/register', details)
    await login(details.phone, details.pin)
  }, [login])

  const retrySession = useCallback(async () => {
    setLoading(true)
    setConnectionError('')
    try {
      const { data } = await apiClient.get('/me')
      setUser(data)
    } catch (error) {
      if (error.response?.status === 401) {
        localStorage.removeItem('camerhits_access_token')
        localStorage.removeItem('camerhits_user')
        setUser(null)
      } else {
        setConnectionError(getApiErrorMessage(error))
      }
    } finally {
      setLoading(false)
    }
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('camerhits_access_token')
    localStorage.removeItem('camerhits_user')
    setConnectionError('')
    setUser(null)
  }, [])

  const value = useMemo(() => ({ user, loading, connectionError, login, register, logout, retrySession }), [user, loading, connectionError, login, register, logout, retrySession])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
