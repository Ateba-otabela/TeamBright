import axios from 'axios'

import { env } from '@/config/env'

export const apiClient = axios.create({
  baseURL: env.apiBaseUrl,
  headers: {
    Accept: 'application/json',
  },
  timeout: 10_000,
})

export function getApiAssetUrl(path: string) {
  return new URL(path, env.apiBaseUrl || window.location.origin).toString()
}

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('camerhits_access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export function getApiErrorMessage(error: unknown, fallback = 'The request could not be completed.') {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data
    if (data && typeof data === 'object') {
      if ('error' in data && data.error && typeof data.error === 'object' && 'message' in data.error) {
        return String(data.error.message)
      }
      if ('detail' in data) {
        const detail = data.detail
        if (typeof detail === 'string') return detail
        if (detail && typeof detail === 'object' && 'message' in detail) return String(detail.message)
      }
    }
    if (!error.response) return 'Could not reach the API. Check the backend connection and API URL.'
  }
  return error instanceof Error ? error.message : fallback
}
