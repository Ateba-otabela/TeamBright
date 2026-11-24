import { apiClient } from './client'

export interface TicketEvent {
  event_id: number
  title: string
  category: string
  venue: string
  city: string
  event_date: string
  total_seats: number
  artist_momo_number: string
  status: string
}

export interface TicketTier {
  id: number
  event_id: number
  name: string
  price: string
  zone_label: string
  quantity: number
  minted: number
}

export interface EventDashboard {
  event: TicketEvent
  total_minted: number
  available: number
  sold: number
  checked_in: number
  gross_momo_revenue: number
  tiers: TicketTier[]
}

export interface GateScanResult {
  valid: boolean
  ticket_code?: string
  buyer_name?: string
  tier?: string
  zone_label?: string
  amount_paid?: number
  reason?: string
}

export async function listEvents() {
  const { data } = await apiClient.get<{ items: TicketEvent[] }>('/api/events')
  return data.items
}

export async function createEvent(event: Omit<TicketEvent, 'event_id' | 'status'>) {
  const { data } = await apiClient.post<TicketEvent>('/api/events', event)
  return data
}

export async function createTicketTier(eventId: number, tier: { name: string; price: string; zone_label: string; quantity: number }): Promise<TicketTier> {
  const { data } = await apiClient.post<TicketTier>(`/api/events/${eventId}/ticket-tiers`, tier)
  return data
}

export async function getEventDashboard(eventId: number): Promise<EventDashboard> {
  const { data } = await apiClient.get<EventDashboard>(`/api/events/${eventId}/dashboard`)
  return data
}

export async function scanGateTicket(ticketCode: string): Promise<GateScanResult> {
  const { data } = await apiClient.post<GateScanResult>('/api/gate/scan', { ticket_code: ticketCode })
  return data
}
