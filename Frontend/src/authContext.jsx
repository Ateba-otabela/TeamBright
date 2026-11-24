import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { apiClient } from './services/api/client'

const AuthContext = createContext(null)

function saveSession(token, user) {
  localStorage.setItem('camerhits_access_token', token)
  localStorage.setItem('camerhits_user', JSON.stringify(user))
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('camerhits_access_token')
    if (!token) {
      setLoading(false)
      return
    }

    let active = true
    apiClient.get('/me')
      .then(({ data }) => { if (active) setUser(data) })
      .catch(() => {
        localStorage.removeItem('camerhits_access_token')
        localStorage.removeItem('camerhits_user')
        if (active) setUser(null)
      })
      .finally(() => { if (active) setLoading(false) })

    return () => { active = false }
  }, [])

  const login = async (phone, pin) => {
    const { data } = await apiClient.post('/auth/login', { phone, pin })
    saveSession(data.access_token, data.user)
    const currentUser = await apiClient.get('/me')
    setUser(currentUser.data)
  }

  const register = async (details) => {
    await apiClient.post('/auth/register', details)
    await login(details.phone, details.pin)
  }

  const logout = () => {
    localStorage.removeItem('camerhits_access_token')
    localStorage.removeItem('camerhits_user')
    setUser(null)
  }

  const value = useMemo(() => ({ user, loading, login, register, logout }), [user, loading])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
