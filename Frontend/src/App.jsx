import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, useLocation, useNavigate, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './authContext'
import { getApiAssetUrl } from './services/api/client'
import Header from './components/Header'
import NavigationDrawer from './components/NavigationDrawer'
import StatCard from './components/StatCard'
import CatalogPage from './pages/CatalogPage'
import PlaceholderPage from './pages/PlaceholderPage'
import EventsTicketsPage from './pages/EventsTicketsPage'
import AIAdvisorPage from './pages/AIAdvisorPage'
import PhoneBroadcastPage from './pages/PhoneBroadcastPage'
import DashboardActions from './components/DashboardActions'
import { DashboardProvider, useDashboard } from './dashboardContext'
import TransactionsPage from './pages/TransactionsPage'
import SplitContractsPage from './pages/SplitContractsPage'
import AuthPage from './pages/AuthPage'
import LandingPage from './pages/LandingPage'
import './dashboard.css'

function HomePage({ onAction }) {
  const { t, overview, overviewLoading, overviewError } = useDashboard()
  const { user } = useAuth()
  const navigate = useNavigate()
  const quickActions = [
    [t.upload, t.uploadDetail, 'upload_file', 'upload'],
    [t.diagnosis, t.diagnosisDetail, 'auto_awesome', 'diagnosis'],
    [t.split, t.splitDetail, 'handshake', 'split'],
    [t.broadcast, t.broadcastDetail, 'phone_in_talk', 'broadcast'],
  ]
  return (
    <main className="dashboard-content">
      <section className="welcome-row"><div><div className="title-line"><h1>{t.welcome}, {user.name}</h1>{user.verified && <span className="verified">✓ {t.verified}</span>}</div><p>{user.city ? `${user.city} · ` : ''}{user.role}</p></div><button className="primary-button" type="button" onClick={() => { navigate('/transactions') }}><span className="material-icon">account_balance_wallet</span>{t.transactions}</button></section>
      <section className="quick-actions" aria-label="Quick actions">{quickActions.map(([label, detail, icon, action]) => <button className="quick-action" type="button" key={label} onClick={() => onAction(action)}><span className="quick-icon material-icon">{icon}</span><span><strong>{label}</strong><small>{detail}</small></span></button>)}</section>
      {overviewError && <p className="form-error" role="alert">{overviewError}</p>}
      <section className="metrics" aria-label="Dashboard statistics">
        <StatCard label="Songs available" value={overviewLoading ? '…' : overview ? String(overview.songs.total) : '—'} detail="Loaded from the songs API" badge="API" />
        <StatCard label="Studio comparisons" value={overviewLoading ? '…' : overview ? String(overview.studio.demos.length) : '—'} detail="Saved SoundDNA analyses" badge="API" />
        <StatCard label="Your events" value={overviewLoading ? '…' : overview ? String(overview.events.total) : '—'} detail="Ticketing events you own" badge="API" />
        <StatCard label="Unread insights" value={overviewLoading ? '…' : overview ? String(overview.advisor.unread_alerts_count) : '—'} detail="Canary advisor alerts" badge="API" />
      </section>
      <section className="content-grid">
        <article className="revenue-card"><div className="revenue-heading"><div><h2>Recent songs</h2><p>Current records from the CamerHits API</p></div><button className="event-outline-button" type="button" onClick={() => navigate('/catalog')}>Open Catalog</button></div>
          {overviewLoading && <p role="status">Loading songs…</p>}
          {!overviewLoading && overview?.songs.items.length === 0 && <p>No songs are available yet.</p>}
          {!overviewLoading && overview?.songs.items.map((song) => <div className="advisor-insight" key={song.id}><div><strong>{song.title}</strong><p>{song.artist_name}</p></div><a href={getApiAssetUrl(song.audio_url)} target="_blank" rel="noreferrer">Play</a></div>)}
        </article>
        <aside className="advisor-card"><div className="advisor-heading"><b>CANARY ADVISOR</b><span className="advisor-badge">LIVE</span></div><h2>{overview?.advisor.weekly_momentum_status?.replaceAll('_', ' ') || 'No release data'}</h2><p>{overview?.advisor.insights?.[0]?.recommendation || 'Release and airplay snapshots will appear here when available.'}</p><button className="primary-button full" type="button" onClick={() => navigate('/ai-advisor')}>Open AI Advisor</button></aside>
      </section>
    </main>
  )
}

function AppShell() {
  const { language, setLanguage, t } = useDashboard()
  const { user, loading, connectionError, retrySession, logout } = useAuth()
  const location = useLocation()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [activeModal, setActiveModal] = useState(null)
  const [darkTheme, setDarkTheme] = useState(true)

  useEffect(() => {
    document.body.classList.toggle('drawer-open', drawerOpen)
    const handleEscape = (event) => event.key === 'Escape' && setDrawerOpen(false)
    document.addEventListener('keydown', handleEscape)
    return () => { document.removeEventListener('keydown', handleEscape); document.body.classList.remove('drawer-open') }
  }, [drawerOpen])

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkTheme)
  }, [darkTheme])
  const closeDrawer = () => setDrawerOpen(false)

  if (loading) {
    return <main className="app-loading" role="status">Connecting to CamerHits…</main>
  }
  if (connectionError && !user) {
    return <main className="api-connection-error" role="alert"><h1>Backend connection failed</h1><p>{connectionError}</p><button className="primary-button" type="button" onClick={retrySession}>Retry connection</button></main>
  }
  if (!user) {
    if (location.pathname === '/login') {
      return <AuthPage initialMode={new URLSearchParams(location.search).get('mode') === 'register' ? 'register' : 'login'} />
    }
    return <LandingPage />
  }
  if (location.pathname === '/login') return <Navigate to="/" replace />

  return (
    <div className="app-shell">
      {drawerOpen && <button className="drawer-backdrop" type="button" aria-label="Close navigation" onClick={closeDrawer} />}
      <NavigationDrawer open={drawerOpen} onClose={closeDrawer} />
      <div className="dashboard">
        <Header drawerOpen={drawerOpen} onOpenDrawer={() => setDrawerOpen(true)} language={language} onToggleLanguage={() => setLanguage((value) => value === 'en' ? 'fr' : 'en')} onToggleTheme={() => setDarkTheme((value) => !value)} themeLabel={darkTheme ? 'Outdoor Light' : 'Studio Dark'} onLogout={logout} />
        <Routes>
          <Route path="/" element={<HomePage onAction={(action) => { setActiveModal(action); setDrawerOpen(false) }} />} />
          <Route path="/catalog" element={<CatalogPage />} />
          <Route path="/catalog-vault" element={<PlaceholderPage title="Catalog Vault" />} />
          <Route path="/events-tickets" element={<EventsTicketsPage />} />
          <Route path="/ai-advisor" element={<AIAdvisorPage />} />
          <Route path="/phone-broadcast" element={<PhoneBroadcastPage />} />
          <Route path="/dj-bounties" element={<PhoneBroadcastPage />} />
          <Route path="/split-contracts" element={<SplitContractsPage />} />
          <Route path="/direct-bookings" element={<PlaceholderPage title="Direct Bookings" />} />
          <Route path="/transactions" element={<TransactionsPage />} />
          <Route path="*" element={<PlaceholderPage title="Page Not Found" />} />
        </Routes>
      </div>
      <DashboardActions activeModal={activeModal} setActiveModal={setActiveModal} />
    </div>
  )
}

export default function App() {
  return <AuthProvider><DashboardProvider><BrowserRouter><AppShell /></BrowserRouter></DashboardProvider></AuthProvider>
}
