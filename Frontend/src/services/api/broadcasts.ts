import { apiClient } from './client'

export interface BroadcastDestination {
  id: number
  label: string
  type: string
  medium: string
  city: string
  is_verified: boolean
}

export interface BroadcastTrack {
  id: number
  title: string
  artist_name: string
  genre: string
  audio_url: string | null
}

export interface BroadcastDispatch {
  id: number
  status: string
  track: BroadcastTrack
  destination: BroadcastDestination
  destination_label: string
  note: string | null
  sent_at: string
}

export async function listBroadcastDestinations() {
  const { data } = await apiClient.get<{ items: BroadcastDestination[] }>('/api/broadcast/destinations')
  return data.items
}

export async function listBroadcastTracks() {
  const { data } = await apiClient.get<{ items: BroadcastTrack[] }>('/api/broadcast/tracks')
  return data.items
}

export async function sendBroadcast(trackId: number, destinationId: number, note = '') {
  const { data } = await apiClient.post<{ executed: boolean; dispatches: BroadcastDispatch[] }>('/api/broadcast/execute', {
    track_id: trackId,
    destination_id: destinationId,
    note: note || undefined,
  })
  return data
}
