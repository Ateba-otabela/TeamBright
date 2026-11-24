import axios from 'axios'

import { env } from '@/config/env'

export const apiClient = axios.create({
  baseURL: env.apiBaseUrl,
  headers: {
    Accept: 'application/json',
  },
  timeout: 10_000,
})

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('camerhits_access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})
