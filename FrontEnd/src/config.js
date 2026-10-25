export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')

export const apiUrl = (path = '/') => {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${API_BASE_URL}${normalizedPath}`
}

/** Fetch helper for the signed-token API. Never place private API/payment secrets in Vite env. */
export const apiFetch = (path = '/', options = {}) => {
  const headers = new Headers(options.headers || {})
  const token = typeof localStorage !== 'undefined' ? localStorage.getItem('savoraToken') : null
  if (token && !headers.has('Authorization')) headers.set('Authorization', `Bearer ${token}`)
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  return fetch(apiUrl(path), { ...options, headers })
}
