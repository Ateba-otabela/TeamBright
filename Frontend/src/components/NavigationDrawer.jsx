import { NavLink } from 'react-router-dom'
import { useDashboard } from '../dashboardContext'
import { useAuth } from '../authContext'

const navigation = [
  { label: 'Home Overview', icon: 'dashboard', to: '/' },
  { label: 'Catalog', icon: 'library_music', to: '/catalog', group: 'B2C • Direct to Fans' },
  { label: 'Events & Tickets', icon: 'confirmation_number', to: '/events-tickets' },
  { label: 'AI Advisor', icon: 'auto_awesome', badge: '1', to: '/ai-advisor', group: 'B2B • Direct Industry' },
  { label: 'Split Contracts', icon: 'handshake', to: '/split-contracts' },
  { label: 'Phone Broadcast', icon: 'phone_in_talk', to: '/phone-broadcast' },
  { label: 'Direct Bookings', icon: 'event_available', to: '/direct-bookings' },
  { label: 'Transactions', icon: 'account_balance_wallet', to: '/transactions' },
]

export default function NavigationDrawer({ open, onClose }) {
  const { t } = useDashboard()
  const { user } = useAuth()
  const initials = (user?.name || 'CH').split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()
  const labels = [t.home, t.catalog, t.events, t.ai, t.splits, t.broadcast, t.bookings, t.transactions]
  const translatedNavigation = navigation.map((item, index) => ({ ...item, label: labels[index] }))
  return (
    <aside id="navigation-drawer" className={`navigation-drawer${open ? ' open' : ''}`} aria-label="Navigation drawer">
      <div>
        <div className="drawer-brand">
          <NavLink className="brand" to="/" onClick={onClose}><span className="brand-mark">C</span><span><strong>CamerHits</strong><small>Direct Studio</small></span></NavLink>
          <button className="icon-button close-button" type="button" onClick={onClose} aria-label="Close navigation">close</button>
        </div>
        <div className="profile-card"><div className="profile-avatar">{initials}</div><div><strong>{user?.name}{user?.verified && <span> ✓</span>}</strong><small>{user?.role}{user?.city ? ` · ${user.city}` : ''}</small></div></div>
        <nav className="drawer-nav" aria-label="Main navigation">
          {translatedNavigation.map((item) => <div className="nav-item-wrap" key={item.label}>{item.group && <span className="nav-group">{item.group}</span>}<NavLink to={item.to} end={item.to === '/'} className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'} onClick={onClose}><span className="material-icon">{item.icon}</span><span>{item.label}</span>{item.badge && <span className="nav-badge">{item.badge}</span>}</NavLink></div>)}
        </nav>
      </div>
      <div className="middlemen-card"><strong><span className="material-icon">bolt</span> No Middlemen</strong><p>Instant MTN MoMo payouts straight to your wallet.</p></div>
    </aside>
  )
}
