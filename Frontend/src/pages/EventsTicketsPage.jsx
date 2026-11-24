import { useState } from 'react'

const eventStats = [
  { label: 'Direct Ticket Revenue', badge: '+24.0%', value: '195,000 XAF', detail: 'Instant MoMo settlement' },
  { label: 'Tickets Sold (B2C)', badge: '68.7% cap', value: '412 / 600', detail: '0% promoter/manager cut' },
  { label: 'Active Live Shows', badge: 'On Sale', value: '2 Events', detail: 'Buea & Douala venues', accentBadge: true },
  { label: 'Offline QR Gate Sync', badge: 'Cached', value: '412 Passes', detail: 'Works without venue Wi-Fi' },
]

function EventStatCard({ stat }) {
  return (
    <article className="event-stat-card">
      <div><span className="event-stat-label">{stat.label}</span><span className={stat.accentBadge ? 'event-stat-badge accent' : 'event-stat-badge'}>{stat.badge}</span></div>
      <strong>{stat.value}</strong>
      <small>{stat.detail}</small>
    </article>
  )
}

function EventCard({ title, status, date, venue, standard, vip, sold, capacity, percent, gradient }) {
  const [copied, setCopied] = useState(false)
  const copyLink = async () => {
    try { await navigator.clipboard?.writeText(`https://camerhits.test/events/${title.toLowerCase().replaceAll(' ', '-')}`) } catch { /* clipboard unavailable */ }
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1800)
  }

  return (
    <article className="event-card">
      <div className="event-card-header">
        <div className="event-main">
          <div className="event-cover" style={{ background: gradient }} aria-hidden="true">♪</div>
          <div>
            <div className="event-title-line"><h2>{title}</h2><span className={status === 'On Sale' ? 'event-status live' : 'event-status'}>{status}</span></div>
            <p className="event-meta">{date} • {venue}</p>
            <p className="event-pricing">Standard: {standard} • VIP Meet &amp; Greet: {vip}</p>
          </div>
        </div>
        <button className="event-outline-button copy-button" type="button" onClick={copyLink}>{copied ? 'Link Copied' : 'Copy Ticket Link'}</button>
      </div>
      <div className="capacity-block">
        <div><span>Capacity Sold: <strong>{sold} / {capacity}</strong></span><strong>{percent}%</strong></div>
        <div className="capacity-track"><span style={{ width: `${percent}%` }} /></div>
      </div>
    </article>
  )
}

function AdvisorCard() {
  const [launched, setLaunched] = useState(false)
  return (
    <article className="event-advisor-card">
      <div className="event-advisor-heading"><span><span className="material-icon">auto_awesome</span>AI ADVISOR</span><b>Douala Boost</b></div>
      <div><h2>Bundle Ticket + Track</h2><p>3,120 Douala listeners streamed your previews this month. Offer a 2,500 XAF early-bird pass with free <em>Midnight Rain</em> download to fill Akwa.</p></div>
      <button className="primary-button full" type="button" onClick={() => setLaunched(true)}>{launched ? 'Early-Bird Launched' : 'Launch 48h Early-Bird'}</button>
    </article>
  )
}

function QRPassPreview() {
  return (
    <article className="qr-pass-card">
      <div><span className="qr-label">Fan QR Pass Preview</span><strong>Buea Town Showcase</strong><small>Pass #CH-TKT-0842 • VIP</small><span className="qr-verified"><span className="material-icon">verified</span>Verified MoMo</span></div>
      <svg viewBox="0 0 64 64" className="ticket-qr" role="img" aria-label="Sample ticket QR code">
        <rect x="4" y="4" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="4"/><rect x="10" y="10" width="6" height="6" fill="currentColor"/><rect x="42" y="4" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="4"/><rect x="48" y="10" width="6" height="6" fill="currentColor"/><rect x="4" y="42" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="4"/><rect x="10" y="48" width="6" height="6" fill="currentColor"/><rect x="28" y="8" width="6" height="6" fill="currentColor"/><rect x="28" y="20" width="6" height="10" fill="currentColor"/><rect x="28" y="36" width="10" height="6" fill="currentColor"/><rect x="44" y="32" width="6" height="12" fill="currentColor"/><rect x="38" y="48" width="18" height="6" fill="currentColor"/><rect x="52" y="40" width="6" height="18" fill="currentColor"/>
      </svg>
    </article>
  )
}

function TicketLedger() {
  const sales = [
    ['#CH-TKT-0842', 'Buea Town Showcase (VIP)', '+237 678 •• •• 21', '4,800 XAF', 'Verified', 'verified'],
    ['#CH-TKT-0841', 'Douala Acoustic Night (Standard)', '+237 651 •• •• 09', '2,880 XAF', 'Offline Cached', 'cached'],
  ]
  return (
    <section className="ticket-ledger">
      <div className="ledger-heading"><h2>Recent Direct MoMo Ticket Sales</h2><span>4% Rail Fee • 0% Middleman</span></div>
      <div className="ledger-table-wrap"><table><thead><tr><th>Ticket ID</th><th>Event &amp; Tier</th><th>MoMo Buyer</th><th>Net to Kamga</th><th>Gate Status</th></tr></thead><tbody>{sales.map((row) => <tr key={row[0]}>{row.slice(0,5).map((cell, index) => <td key={index} className={index === 3 ? 'ledger-net' : index === 1 ? 'ledger-event' : ''}>{index === 4 ? <span className={`gate-status ${row[5]}`}>{cell}</span> : cell}</td>)}</tr>)}</tbody></table></div>
    </section>
  )
}

export default function EventsTicketsPage() {
  const [gateOpen, setGateOpen] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)

  return (
    <main className="events-page">
      <section className="events-title-row">
        <div><h1>Events &amp; Direct Ticketing</h1><p>Sell B2C show tickets directly via MTN MoMo with offline QR gate verification and zero ticketing middlemen.</p></div>
        <div className="events-actions"><button className="event-outline-button" type="button" onClick={() => setGateOpen((value) => !value)}><span className="material-icon">qr_code_scanner</span>{gateOpen ? 'Close Gate Scanner' : 'Open Gate Scanner'}</button><button className="primary-button" type="button" onClick={() => setCreateOpen((value) => !value)}><span className="material-icon">add</span>Create Direct Event</button></div>
      </section>

      {gateOpen && <div className="event-panel" role="status"><span className="material-icon">qr_code_scanner</span><div><strong>Offline Gate Scanner Ready</strong><small>412 passes cached and ready for venue verification.</small></div></div>}
      {createOpen && <div className="event-panel" role="dialog" aria-label="Create direct event"><span className="material-icon">event_available</span><div><strong>New Direct Event</strong><small>Event creation controls are ready to connect to your booking workflow.</small></div><button type="button" onClick={() => setCreateOpen(false)}>Dismiss</button></div>}

      <section className="event-stats">{eventStats.map((stat) => <EventStatCard key={stat.label} stat={stat} />)}</section>

      <section className="events-grid">
        <div className="event-list">
          <EventCard title="Buea Town Live Showcase" status="On Sale" date="Sat, Dec 20, 2026 • 20:00 WAT" venue="Mountain Hotel, Buea" standard="2,500 XAF" vip="5,000 XAF" sold="280" capacity="350" percent="80" gradient="linear-gradient(135deg,#382d12,#f4c430)" />
          <EventCard title="Douala Akwa Acoustic Night" status="On Sale" date="Sat, Jan 10, 2027 • 21:00 WAT" venue="Canal Olympia, Douala" standard="3,000 XAF" vip="7,500 XAF" sold="132" capacity="250" percent="53" gradient="linear-gradient(135deg,#192442,#f4c430)" />
        </div>
        <div className="event-sidebar-panels"><AdvisorCard /><QRPassPreview /></div>
      </section>

      <TicketLedger />
    </main>
  )
}
