import { useState } from 'react'
import { useAuth } from '../authContext'
import './AuthPage.css'

const roleOptions = [
  ['fan', 'Fan & Listener'],
  ['artist', 'Artist / Producer'],
  ['dj', 'DJ'],
  ['broadcaster', 'Broadcaster'],
  ['promoter', 'Event Promoter'],
  ['collaborator', 'Collaborator'],
]

function getErrorMessage(error) {
  return error.response?.data?.error?.message || error.response?.data?.detail?.message ||
    error.response?.data?.detail || error.message || 'Unable to connect to CamerHits'
}

export default function AuthPage({ initialMode = 'login' }) {
  const { login, register } = useAuth()
  const [mode, setMode] = useState(initialMode)
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [pin, setPin] = useState('')
  const [role, setRole] = useState('fan')
  const [city, setCity] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const isRegister = mode === 'register'

  const submit = async (event) => {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      if (isRegister) await register({ name, phone, pin, role, city })
      else await login(phone, pin)
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <div className="auth-brand"><span className="brand-mark">C</span><span><strong>CamerHits</strong><small>Direct Studio</small></span></div>
        <div>
          <h1>{isRegister ? 'Create your account' : 'Welcome back'}</h1>
          <p>Sign in to manage your music, broadcasts, and events.</p>
        </div>
        <div className="auth-tabs" role="tablist" aria-label="Account access">
          <button type="button" role="tab" aria-selected={!isRegister} className={!isRegister ? 'active' : ''} onClick={() => { setMode('login'); setError('') }}>Login</button>
          <button type="button" role="tab" aria-selected={isRegister} className={isRegister ? 'active' : ''} onClick={() => { setMode('register'); setError('') }}>Register</button>
        </div>
        <form className="auth-form" onSubmit={submit}>
          {isRegister && <>
            <label>Full name<input required autoComplete="name" value={name} onChange={(event) => setName(event.target.value)} /></label>
            <label>Account role<select value={role} onChange={(event) => setRole(event.target.value)}>{roleOptions.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
            <label>City<input required autoComplete="address-level2" value={city} onChange={(event) => setCity(event.target.value)} /></label>
          </>}
          <label>Cameroon phone<input required type="tel" autoComplete="tel" placeholder="+237 6XX XXX XXX" value={phone} onChange={(event) => setPhone(event.target.value)} /></label>
          <label>PIN<input required type="password" inputMode="numeric" autoComplete={isRegister ? 'new-password' : 'current-password'} pattern="[0-9]{4,6}" minLength={4} maxLength={6} value={pin} onChange={(event) => setPin(event.target.value)} /></label>
          {error && <p className="auth-error" role="alert">{error}</p>}
          <button type="submit" className="auth-submit" disabled={submitting}>{submitting ? 'Connecting…' : isRegister ? 'Create account' : 'Sign in'}</button>
        </form>
      </section>
    </main>
  )
}
