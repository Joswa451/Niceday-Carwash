const fallbackBase = import.meta.env.DEV ? 'http://localhost:5000/api' : '/api'
const rawBase = (import.meta.env.VITE_API_URL || fallbackBase).replace(/\/+$/, '')

export const API_URL = /\/api$/i.test(rawBase) ? rawBase : `${rawBase}/api`

export async function apiRequest(path, { method = 'GET', body, token } = {}) {
  const headers = {}
  if (body) headers['Content-Type'] = 'application/json'
  if (token) headers.Authorization = `Bearer ${token}`

  const response = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })

  const data = await response.json().catch(() => null)

  if (!response.ok) {
    const error = new Error(data?.error || `Request failed (${response.status})`)
    error.status = response.status
    error.data = data
    throw error
  }

  return data
}
