import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom'
import Header from './components/Header'
import NavigationDrawer from './components/NavigationDrawer'
import StatCard from './components/StatCard'
import RevenueChart from './components/RevenueChart'
import AdvisorPanel from './components/AdvisorPanel'
import CatalogPage from './pages/CatalogPage'
import PlaceholderPage from './pages/PlaceholderPage'
import EventsTicketsPage from './pages/EventsTicketsPage'
import AIAdvisorPage from './pages/AIAdvisorPage'
import PhoneBroadcastPage from './pages/PhoneBroadcastPage'
import DashboardActions from './components/DashboardActions'
import { DashboardProvider, useDashboard } from './dashboardContext'
import TransactionsPage from './pages/TransactionsPage'
import SplitContractsPage from './pages/SplitContractsPage'
import './dashboard.css'

function HomePage({ onAction }) {
  const { t } = useDashboard()
  const navigate = useNavigate()
  const quickActions = [
    [t.upload, t.uploadDetail, 'upload_file', 'upload'],
    [t.diagnosis, t.diagnosisDetail, 'auto_awesome', 'diagnosis'],
    [t.split, t.splitDetail, 'handshake', 'split'],
    [t.broadcast, t.broadcastDetail, 'phone_in_talk', 'broadcast'],
  ]
  return (
    <main className="dashboard-content">
      <section className="welcome-row"><div><div className="title-line"><h1>{t.welcome}</h1><span className="verified">✓ {t.verified}</span></div><p>{t.welcomeDetail}</p></div><button className="primary-button" type="button" onClick={() => { navigate('/transactions') }}><span className="material-icon">account_balance_wallet</span>{t.transactions}</button></section>
      <section className="quick-actions" aria-label="Quick actions">{quickActions.map(([label, detail, icon, action]) => <button className="quick-action" type="button" key={label} onClick={() => onAction(action)}><span className="quick-icon material-icon">{icon}</span><span><strong>{label}</strong><small>{detail}</small></span></button>)}</section>
      <section className="metrics" aria-label="Dashboard statistics"><StatCard label={t.earnings} value="482,500 XAF" detail="312,000 B2C • 170,500 B2B" badge="+18.4%" /><StatCard label={t.sales} value="340 Sales" detail="7,000 previews across 2 tracks" badge="4.86% conv" /><StatCard label={t.spins} value="621 Spins" detail="450 Buea Town • 171 Midnight Rain" badge="55.8pt" /><StatCard label={t.bountiesMetric} value="15,000 XAF" detail="Douala DJ Bounty + 1 Live Request" badge="Escrowed" /></section>
      <section className="content-grid"><RevenueChart /><AdvisorPanel onInspect={() => onAction('inspect')} /></section>
    </main>
  )
}

function AppShell() {
  const { language, setLanguage, t } = useDashboard()
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

  return (
    <div className="app-shell">
      {drawerOpen && <button className="drawer-backdrop" type="button" aria-label="Close navigation" onClick={closeDrawer} />}
      <NavigationDrawer open={drawerOpen} onClose={closeDrawer} />
      <div className="dashboard">
        <Header drawerOpen={drawerOpen} onOpenDrawer={() => setDrawerOpen(true)} language={language} onToggleLanguage={() => setLanguage((value) => value === 'en' ? 'fr' : 'en')} onToggleTheme={() => setDarkTheme((value) => !value)} themeLabel={darkTheme ? 'Outdoor Light' : 'Studio Dark'} />
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
  return <DashboardProvider><BrowserRouter><AppShell /></BrowserRouter></DashboardProvider>
}
