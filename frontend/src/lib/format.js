export const PAYMENT_LABELS = {
  cash: 'Cash',
  gcash: 'GCash',
  maya: 'Maya',
  bank_transfer: 'Bank Transfer',
}

export const ONLINE_PAYMENT_METHODS = ['gcash', 'maya', 'bank_transfer']

export function paymentLabel(value) {
  return PAYMENT_LABELS[value] || String(value || '').replace(/_/g, ' ')
}

export function statusLabel(value) {
  return String(value || '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

export function formatMoney(value) {
  const number = Number(value)
  if (!Number.isFinite(number)) return value ?? ''
  return number.toLocaleString('en-PH', {
    minimumFractionDigits: number % 1 === 0 ? 0 : 2,
    maximumFractionDigits: 2,
  })
}

export function formatDate(value) {
  if (!value) return 'N/A'
  const text = String(value)
  const date = /^\d{4}-\d{2}-\d{2}$/.test(text)
    ? new Date(`${text}T00:00:00`)
    : new Date(text)
  if (Number.isNaN(date.getTime())) return text
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: '2-digit',
    year: 'numeric',
  })
}

export function formatTime(value) {
  if (!value) return 'N/A'
  const text = String(value)
  const match = text.match(/^(\d{2}):(\d{2})/)
  if (match) {
    const date = new Date()
    date.setHours(Number(match[1]), Number(match[2]), 0, 0)
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
    })
  }
  const date = new Date(text)
  if (Number.isNaN(date.getTime())) return text
  return date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  })
}

export function formatDateTime(value) {
  if (!value) return 'N/A'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString('en-US', {
    month: 'short',
    day: '2-digit',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

export function todayInputValue() {
  const now = new Date()
  const offset = now.getTimezoneOffset() * 60000
  return new Date(now.getTime() - offset).toISOString().slice(0, 10)
}
