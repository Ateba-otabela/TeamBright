import { useCallback, useEffect, useMemo, useState } from 'react'
import { useAuth } from '../authContext'
import { useDashboard } from '../dashboardContext'
import { getApiErrorMessage } from '../services/api/client'
import { createEvent, createTicketTier, getEventDashboard, listEvents, scanGateTicket } from '../services/api/events'

const emptyEvent = {
  title: '',
  category: 'concert',
  venue: '',
  city: '',
  event_date: '',
  total_seats: '100',
  artist_momo_number: '',
  tier_name: 'Standard',
  ticket_price: '',
  zone_label: 'General admission',
}

function EventCard({ dashboard }) {
  const { event } = dashboard
  const capacity = event.total_seats || 0
  const sold = dashboard.sold || 0
  const percent = capacity ? Math.min(100, Math.round((sold / capacity) * 100)) : 0

  return (
    <article className="event-card">
      <div className="event-card-header">
        <div className="event-main">
          <div className="event-cover" aria-hidden="true">♪</div>
          <div>
            <div className="event-title-line"><h2>{event.title}</h2><span className="event-status">{event.status}</span></div>
            <p className="event-meta">{new Date(event.event_date).toLocaleString()} · {event.venue}, {event.city}</p>
            <p className="event-pricing">{(dashboard.tiers || []).map((tier) => `${tier.name}: ${Number(tier.price).toLocaleString()} XAF`).join(' · ') || 'No ticket tiers created'}</p>
          </div>
        </div>
      </div>
      <div className="capacity-block">
        <div><span>Tickets sold: <strong>{sold} / {capacity}</strong></span><strong>{percent}%</strong></div>
        <div className="capacity-track"><span style={{ width: `${percent}%` }} /></div>
        <small>{Number(dashboard.gross_momo_revenue || 0).toLocaleString()} XAF gross MoMo revenue</small>
      </div>
    </article>
  )
}

function EventStatCard({ label, value, detail }) {
  return <article className="event-stat-card"><div><span className="event-stat-label">{label}</span></div><strong>{value}</strong><small>{detail}</small></article>
}

export default function EventsTicketsPage() {
  const { user } = useAuth()
  const { refreshOverview } = useDashboard()
  const [dashboards, setDashboards] = useState([])
  const [loading, setLoading] = useState(true)
  const [createOpen, setCreateOpen] = useState(false)
  const [gateOpen, setGateOpen] = useState(false)
  const [form, setForm] = useState(emptyEvent)
  const [gateCode, setGateCode] = useState('')
  const [gateResult, setGateResult] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [saving, setSaving] = useState(false)
  const canManageEvents = ['artist', 'promoter'].includes(user?.role)
  const canScanTickets = canManageEvents || user?.role === 'admin'

  const loadEvents = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const events = await listEvents()
      const eventDashboards = await Promise.all(events.map((event) => getEventDashboard(event.event_id)))
      setDashboards(eventDashboards)
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Could not load events.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadEvents() }, [loadEvents])

  const totals = useMemo(() => dashboards.reduce((result, item) => ({
    capacity: result.capacity + item.event.total_seats,
    sold: result.sold + item.sold,
    revenue: result.revenue + Number(item.gross_momo_revenue || 0),
    minted: result.minted + item.total_minted,
  }), { capacity: 0, sold: 0, revenue: 0, minted: 0 }), [dashboards])

  const submitEvent = async (event) => {
    event.preventDefault()
    setSaving(true)
    setError('')
    setNotice('')
    try {
      const created = await createEvent({
        title: form.title.trim(),
        category: form.category,
        venue: form.venue.trim(),
        city: form.city.trim(),
        event_date: new Date(form.event_date).toISOString(),
        total_seats: Number(form.total_seats),
        artist_momo_number: form.artist_momo_number.trim(),
      })
      let tierFailureMessage = ''
      try {
        await createTicketTier(created.event_id, {
          name: form.tier_name.trim(),
          price: form.ticket_price,
          zone_label: form.zone_label.trim(),
          quantity: Number(form.total_seats),
        })
        setNotice('Event and ticket tier created. The event is pending admin approval.')
      } catch (tierError) {
        setNotice('Event was created, but its ticket tier could not be created.')
        tierFailureMessage = getApiErrorMessage(tierError)
      }
      setForm(emptyEvent)
      setCreateOpen(false)
      await loadEvents()
      await refreshOverview()
      if (tierFailureMessage) setError(tierFailureMessage)
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Could not create the event.'))
    } finally {
      setSaving(false)
    }
  }

  const submitGateScan = async (event) => {
    event.preventDefault()
    setError('')
    setGateResult(null)
    try {
      setGateResult(await scanGateTicket(gateCode.trim()))
      setGateCode('')
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Could not verify this ticket.'))
    }
  }

  return (
    <main className="events-page">
      <section className="events-title-row">
        <div><h1>Events &amp; Direct Ticketing</h1><p>Create events and ticket tiers, monitor sales, and verify gate tickets using the CamerHits API.</p></div>
        <div className="events-actions">{canScanTickets && <button className="event-outline-button" type="button" onClick={() => { setGateOpen((value) => !value); setError(''); setGateResult(null) }}><span className="material-icon">qr_code_scanner</span>{gateOpen ? 'Close Gate Scanner' : 'Open Gate Scanner'}</button>}{canManageEvents && <button className="primary-button" type="button" onClick={() => { setCreateOpen((value) => !value); setError('') }}><span className="material-icon">add</span>Create Event</button>}</div>
      </section>

      {error && <p className="form-error" role="alert">{error}</p>}
      {notice && <p role="status">{notice}</p>}

      {gateOpen && canScanTickets && <form className="event-panel" onSubmit={submitGateScan}><span className="material-icon">qr_code_scanner</span><label><strong>Verify ticket code</strong><input value={gateCode} onChange={(event) => setGateCode(event.target.value)} required placeholder="CH-…" /></label><button className="event-outline-button" type="submit">Scan ticket</button>{gateResult && <small role="status">{gateResult.valid ? `Valid ticket · ${gateResult.ticket_code}` : gateResult.reason}</small>}</form>}

      {createOpen && canManageEvents && <form className="event-panel event-create-form" onSubmit={submitEvent}>
        <h2>New direct event</h2>
        <div className="form-grid"><label><span>Event name *</span><input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} maxLength={200} required /></label><label><span>Category *</span><select value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })}><option value="concert">Concert</option><option value="conference">Conference</option><option value="wedding">Wedding</option><option value="other">Other</option></select></label></div>
        <div className="form-grid"><label><span>Venue *</span><input value={form.venue} onChange={(event) => setForm({ ...form, venue: event.target.value })} required /></label><label><span>City *</span><input value={form.city} onChange={(event) => setForm({ ...form, city: event.target.value })} required /></label></div>
        <div className="form-grid"><label><span>Date &amp; time *</span><input type="datetime-local" value={form.event_date} onChange={(event) => setForm({ ...form, event_date: event.target.value })} required /></label><label><span>Total tickets *</span><input type="number" min="1" value={form.total_seats} onChange={(event) => setForm({ ...form, total_seats: event.target.value })} required /></label></div>
        <div className="form-grid"><label><span>Ticket tier *</span><input value={form.tier_name} onChange={(event) => setForm({ ...form, tier_name: event.target.value })} required /></label><label><span>Ticket price (XAF) *</span><input type="number" min="0" step="0.01" value={form.ticket_price} onChange={(event) => setForm({ ...form, ticket_price: event.target.value })} required /></label></div>
        <div className="form-grid"><label><span>Ticket zone *</span><input value={form.zone_label} onChange={(event) => setForm({ ...form, zone_label: event.target.value })} required /></label><label><span>Organizer MoMo number *</span><input type="tel" value={form.artist_momo_number} onChange={(event) => setForm({ ...form, artist_momo_number: event.target.value })} required /></label></div>
        <div className="form-actions"><button className="event-outline-button" type="button" onClick={() => setCreateOpen(false)}>Cancel</button><button className="primary-button" type="submit" disabled={saving}>{saving ? 'Creating…' : 'Create event & tier'}</button></div>
      </form>}

      <section className="event-stats">
        <EventStatCard label="Direct Ticket Revenue" value={`${totals.revenue.toLocaleString()} XAF`} detail="Gross payments recorded by the backend" />
        <EventStatCard label="Tickets Sold" value={`${totals.sold} / ${totals.capacity}`} detail="Across your events" />
        <EventStatCard label="Events" value={String(dashboards.length)} detail={`${dashboards.filter((item) => item.event.status === 'approved').length} approved · ${dashboards.filter((item) => item.event.status === 'pending').length} pending`} />
        <EventStatCard label="Tickets Minted" value={String(totals.minted)} detail="Available and sold tickets" />
      </section>

      <section className="events-grid">
        <div className="event-list">
          {loading && <p role="status">Loading events…</p>}
          {!loading && dashboards.map((dashboard) => <EventCard key={dashboard.event.event_id} dashboard={dashboard} />)}
          {!loading && !error && dashboards.length === 0 && <p>No events yet. Create an event to get started.</p>}
        </div>
        <aside className="event-sidebar-panels">
          <article className="event-advisor-card"><div className="event-advisor-heading"><span><span className="material-icon">info</span> EVENT STATUS</span></div><div><h2>Approval required</h2><p>New events are created as pending. Ticket sales open only after an administrator approves the event and tickets are minted.</p></div></article>
          <article className="qr-pass-card"><div><span className="qr-label">Gate verification</span><strong>Live API check</strong><small>Use the scanner above to validate a ticket code against the backend.</small></div><span className="material-icon">verified</span></article>
        </aside>
      </section>
    </main>
  )
}
