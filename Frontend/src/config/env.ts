const apiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim() || '/api/v1'

export const env = {
  apiBaseUrl,
} as const
