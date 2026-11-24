import { useState } from 'react'
import { useDashboard } from '../dashboardContext'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../authContext'

export default function Header({ drawerOpen, onOpenDrawer, language, onToggleLanguage, onToggleTheme, themeLabel, onLogout }) {
  const { t, notifications, unreadCount, openNotification, markAllRead, walletBalance } = useDashboard()
  const { user } = useAuth()
  const [panelOpen, setPanelOpen] = useState(false)
  const [opened, setOpened] = useState(null)
  const roleLabels = { artist: t.artist, dj: t.dj, broadcaster: t.broadcaster, collaborator: t.collaborator, promoter: t.promoter, fan: t.fan, admin: t.admin }
  const roles = Object.values(roleLabels)
  const navigate = useNavigate()

  return (
    <header className="topbar">
      <div className="header-left">
        <button className="burger icon-button" type="button" aria-label={t.openNav} aria-controls="navigation-drawer" aria-expanded={drawerOpen} onClick={onOpenDrawer}>
          <span /><span /><span />
        </button>
        <span className="role-label">{t.role}:</span>
        <div className="role-switcher" aria-label={t.role}>
          {roles.map((role) => <button type="button" key={role} className={role === roleLabels[user?.role] ? 'active' : ''}>{role}</button>)}
        </div>
      </div>
      <div className="topbar-actions">
        <button className="control" type="button" onClick={onToggleLanguage}>{t.language}</button>
        <button className="control theme-control" type="button" onClick={onToggleTheme}><span className="material-icon">contrast</span>{themeLabel}</button>
        <button className="control" type="button" onClick={onLogout}>Sign out</button>
        <div className="notification-wrap">
          <button className="icon-button notification" type="button" aria-label={`${t.notifications} (${unreadCount})`} aria-expanded={panelOpen} onClick={() => setPanelOpen((value) => !value)}>
            notifications{unreadCount > 0 && <span className="notification-count">{unreadCount}</span>}
          </button>
          {panelOpen && (
            <section className="notification-panel" role="dialog" aria-label={t.notifications}>
              <header>
                <strong>{t.notifications}</strong>
                <button type="button" onClick={markAllRead}>{t.markAllRead}</button>
              </header>
              {notifications.map((item) => (
                <button type="button" className={`notification-item${item.read ? ' read' : ''}`} key={item.id} onClick={() => { openNotification(item.id); setOpened(opened?.id === item.id ? null : item) }}>
                  <span className="notification-dot" />
                  <span>
                    <strong>{language === 'fr' ? item.titleFr : item.title}</strong>
                    <small>{language === 'fr' ? item.detailFr : item.detail}</small>
                    {opened?.id === item.id && <em>{t.notificationOpened}</em>}
                  </span>
                </button>
              ))}
              {notifications.length === 0 && <p>{t.noNotifications}</p>}
            </section>
          )}
        </div>
        <button className="wallet" type="button" onClick={() => navigate('/transactions')}><span className="material-icon">account_balance_wallet</span>{walletBalance.toLocaleString()} XAF</button>
      </div>
    </header>
  )
}
