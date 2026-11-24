import { apiClient, getApiAssetUrl } from './client'

export interface Song {
  id: number
  title: string
  artist_name: string
  audio_url: string
  audio_size: number
  created_at: string
}

export async function listMySongs() {
  const { data } = await apiClient.get<{ items: Song[] }>('/songs/mine')
  return data.items
}

export async function listRecentSongs() {
  const { data } = await apiClient.get<{ items: Song[] }>('/songs/recent')
  return data.items
}

export async function uploadSong(title: string, audioFile: File): Promise<Song> {
  const formData = new FormData()
  formData.append('title', title)
  formData.append('audio_file', audioFile)
  const { data } = await apiClient.post<Song>('/songs', formData, { timeout: 120_000 })
  return data
}

export async function registerBroadcastTrack(song: Song, genre: string) {
  const { data } = await apiClient.post('/api/tracks', {
    title: song.title,
    artist_name: song.artist_name,
    genre,
    audio_url: getApiAssetUrl(song.audio_url),
  })
  return data
}
