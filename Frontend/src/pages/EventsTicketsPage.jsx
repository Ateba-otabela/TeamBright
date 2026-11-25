import { useEffect, useRef, useState } from 'react'
import DashboardModal from '../components/DashboardModal'
import QRCode from 'qrcode'

const createdEventsStorageKey = 'camerhits-direct-events-v1'

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

function EventCard({ title, status, date, venue, standard, vip, sold, capacity, percent, cover, coverAlt }) {
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
          {cover ? <img className="event-cover" src={cover} alt={coverAlt} /> : <div className="event-cover event-cover-placeholder" aria-hidden="true"><span className="material-icon">event</span></div>}
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

function CreateEventForm({ onCreate, onCancel }) {
  const [form, setForm] = useState({ title: '', venue: '', date: '', capacity: '', standard: '', vip: '' })
  const [error, setError] = useState('')
  const update = (field) => (event) => setForm((current) => ({ ...current, [field]: event.target.value }))

  const submit = (event) => {
    event.preventDefault()
    const capacity = Number(form.capacity)
    const standard = Number(form.standard)
    const vip = Number(form.vip)
    if (new Date(form.date).getTime() <= Date.now()) {
      setError('Choose an event date and time in the future.')
      return
    }
    if (!form.title.trim() || !form.venue.trim() || capacity < 1 || standard < 1 || vip < standard) {
      setError('Enter a ticket capacity, a valid standard price, and a VIP price at least as high as the standard price.')
      return
    }
    onCreate({
      id: `event-${Date.now()}`,
      title: form.title.trim(),
      venue: form.venue.trim(),
      date: new Date(form.date).toLocaleString([], { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' }),
      capacity,
      standard: `${standard.toLocaleString()} XAF`,
      vip: `${vip.toLocaleString()} XAF`,
      sold: 0,
      percent: 0,
      status: 'Draft',
      cover: '',
      coverAlt: `${form.title.trim()} event`
    })
  }

  return (
    <form className="dashboard-form" onSubmit={submit}>
      <div className="form-note">Create an event draft with ticket tiers and capacity. Publishing and MoMo payments are not connected yet.</div>
      <label><span>Event name *</span><input value={form.title} onChange={update('title')} maxLength="80" required placeholder="e.g. Buea Live Showcase" /></label>
      <label><span>Venue and city *</span><input value={form.venue} onChange={update('venue')} maxLength="120" required placeholder="e.g. Mountain Hotel, Buea" /></label>
      <label><span>Date and time *</span><input type="datetime-local" value={form.date} onChange={update('date')} required /></label>
      <div className="form-grid">
        <label><span>Ticket capacity *</span><input type="number" min="1" step="1" value={form.capacity} onChange={update('capacity')} required /></label>
        <label><span>Standard ticket (XAF) *</span><input type="number" min="1" step="1" value={form.standard} onChange={update('standard')} required /></label>
      </div>
      <label><span>VIP ticket (XAF) *</span><input type="number" min={form.standard || 1} step="1" value={form.vip} onChange={update('vip')} required /></label>
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="form-actions"><button type="button" className="secondary-button" onClick={onCancel}>Cancel</button><button type="submit" className="primary-button">Save Event Draft</button></div>
    </form>
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
  const canvasRef = useRef(null)
  const [qrReady, setQrReady] = useState(false)
  const ticketPayload = 'CAMERHITS TICKET PREVIEW\nTicket ID: CH-TKT-0842\nEvent: Buea Town Live Showcase\nTier: VIP\nStatus: PREVIEW ONLY — NOT VALID FOR ENTRY'

  useEffect(() => {
    let active = true
    QRCode.toCanvas(canvasRef.current, ticketPayload, {
      width: 176,
      margin: 2,
      errorCorrectionLevel: 'M',
      color: { dark: '#101827', light: '#ffffff' }
    }).then(() => { if (active) setQrReady(true) }).catch(() => { if (active) setQrReady(false) })
    return () => { active = false }
  }, [ticketPayload])

  const downloadQr = () => {
    const link = document.createElement('a')
    link.download = 'camerhits-ticket-preview-CH-TKT-0842.png'
    link.href = canvasRef.current?.toDataURL('image/png') || ''
    link.click()
  }

  return (
    <article className="qr-pass-card">
      <div><span className="qr-label">Scannable Ticket Preview</span><strong>Buea Town Showcase</strong><small>Pass #CH-TKT-0842 • VIP</small><span className="qr-verified"><span className="material-icon">info</span>Preview only · not valid for entry</span></div>
      <div className="ticket-qr-wrap"><canvas ref={canvasRef} className="ticket-qr" role="img" aria-label={`Scannable QR with ticket details: ${ticketPayload.replaceAll('\n', ', ')}`} />{qrReady && <button type="button" className="qr-download-button" onClick={downloadQr}>Download QR</button>}</div>
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
  const [createdEvents, setCreatedEvents] = useState(() => {
    try {
      const storedEvents = JSON.parse(localStorage.getItem(createdEventsStorageKey) || '[]')
      return Array.isArray(storedEvents) ? storedEvents : []
    } catch { return [] }
  })
  const [createSuccess, setCreateSuccess] = useState(false)
  useEffect(() => {
    try { localStorage.setItem(createdEventsStorageKey, JSON.stringify(createdEvents)) } catch { /* storage may be unavailable */ }
  }, [createdEvents])

  const createEvent = (event) => {
    setCreatedEvents((events) => [event, ...events])
    setCreateOpen(false)
    setCreateSuccess(true)
    window.setTimeout(() => setCreateSuccess(false), 3500)
  }

  return (
    <main className="events-page">
      <section className="events-title-row">
        <div><h1>Events &amp; Direct Ticketing</h1><p>Sell B2C show tickets directly via MTN MoMo with offline QR gate verification and zero ticketing middlemen.</p></div>
        <div className="events-actions"><button className="event-outline-button" type="button" onClick={() => setGateOpen((value) => !value)}><span className="material-icon">qr_code_scanner</span>{gateOpen ? 'Close Gate Scanner' : 'Open Gate Scanner'}</button><button className="primary-button" type="button" onClick={() => setCreateOpen((value) => !value)}><span className="material-icon">add</span>Create Direct Event</button></div>
      </section>

      {gateOpen && <div className="event-panel" role="status"><span className="material-icon">qr_code_scanner</span><div><strong>Offline Gate Scanner Ready</strong><small>412 passes cached and ready for venue verification.</small></div></div>}
      {createSuccess && <div className="event-panel" role="status"><span className="material-icon">event_available</span><div><strong>Event draft saved</strong><small>Your event has been added to this page. You can review it in the event list.</small></div><button type="button" onClick={() => setCreateSuccess(false)}>Dismiss</button></div>}

      <section className="event-stats">{eventStats.map((stat) => <EventStatCard key={stat.label} stat={stat} />)}</section>

      <section className="events-grid">
        <div className="event-list">
          {createdEvents.map((event) => <EventCard key={event.id} {...event} />)}
          <EventCard title="Buea Town Live Showcase" status="On Sale" date="Sat, Dec 20, 2026 • 20:00 WAT" venue="Mountain Hotel, Buea" standard="2,500 XAF" vip="5,000 XAF" sold="280" capacity="350" percent="80" cover="/covers/events/buea-town-live-showcase.jpg" coverAlt="Buea Town Live Showcase event poster" />
          <EventCard title="Douala Akwa Acoustic Night" status="On Sale" date="Sat, Jan 10, 2027 • 21:00 WAT" venue="Canal Olympia, Douala" standard="3,000 XAF" vip="7,500 XAF" sold="132" capacity="250" percent="53" cover="/covers/events/douala-akwa-acoustic-night.jpg" coverAlt="Live music crowd at an outdoor concert" />
        </div>
        <div className="event-sidebar-panels"><AdvisorCard /><QRPassPreview /></div>
      </section>

      <TicketLedger />

      <DashboardModal open={createOpen} title="Create Direct Event" eyebrow="Events & Ticketing" onClose={() => setCreateOpen(false)}>
        <CreateEventForm onCreate={createEvent} onCancel={() => setCreateOpen(false)} />
      </DashboardModal>
    </main>
  )
}
