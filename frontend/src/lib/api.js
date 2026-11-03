const configuredBase = (import.meta.env.VITE_API_URL || '').trim()
const developmentBase = import.meta.env.DEV ? 'http://localhost:5000/api' : ''

function normalizeApiBase(value) {
  const trimmed = value.trim()
  if (!trimmed) return ''

  let parsed
  try {
    parsed = new URL(trimmed)
  } catch {
    return ''
  }

  if (!['http:', 'https:'].includes(parsed.protocol)) return ''

  const path = parsed.pathname.replace(/\/+$/, '')
  const apiPath = /\/api$/i.test(path) ? path : `${path}/api`
  return `${parsed.origin}${apiPath}`
}

export const API_URL = normalizeApiBase(configuredBase || developmentBase)

export const API_CONFIG_ERROR = API_URL
  ? ''
  : 'The API URL is not configured. Set VITE_API_URL on Vercel to the Render backend URL ending in /api.'

function requestError(message, status = 0, extra = {}) {
  const error = new Error(message)
  error.status = status
  Object.assign(error, extra)
  return error
}

function apiEndpoint(path) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${API_URL}${normalizedPath}`
}

export async function apiRequest(path, { method = 'GET', body, token } = {}) {
  if (!API_URL) {
    throw requestError(API_CONFIG_ERROR, 0, { code: 'API_CONFIG' })
  }

  const headers = { Accept: 'application/json' }
  if (body) headers['Content-Type'] = 'application/json'
  if (token) headers.Authorization = `Bearer ${token}`

  let response
  try {
    response = await fetch(apiEndpoint(path), {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch (cause) {
    throw requestError(
      'Could not reach the backend API. Check that the Render service is running and that VITE_API_URL is correct.',
      0,
      { cause },
    )
  }

  const contentType = response.headers.get('content-type') || ''
  const isJson = contentType.toLowerCase().includes('application/json')

  let data = null
  if (isJson) {
    data = await response.json().catch(() => null)
  } else {
    await response.text().catch(() => '')
  }

  if (!response.ok) {
    let message = typeof data?.error === 'string' ? data.error : ''
    if (!message && response.status === 405) {
      message = `The backend did not allow ${method} ${path}. Check that VITE_API_URL points to the Render API, not the Vercel frontend.`
    }
    if (!message) {
      message = `Request failed (${response.status}).`
    }
    throw requestError(message, response.status, { data })
  }

  if (!isJson || data === null) {
    throw requestError(
      'The API returned a non-JSON response. Check that VITE_API_URL points to the Render backend and ends with /api.',
      response.status,
      { data: null },
    )
  }

  return data
}
