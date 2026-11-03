import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { apiRequest } from '../lib/api'

export default function ChangePasswordPage() {
  const { user, token, updateToken } = useAuth()
  const { notify } = useToast()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const handleChange = (event) => {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    if (form.new_password.length < 8) {
      setError('New password must be at least 8 characters long.')
      return
    }
    if (form.new_password !== form.confirm_password) {
      setError('New passwords do not match.')
      return
    }
    setBusy(true)
    try {
      const result = await apiRequest('/auth/change-password', {
        method: 'POST',
        token,
        body: form,
      })
      if (result?.data?.token) updateToken(result.data.token)
      notify(result.message || 'Password updated successfully.', 'success')
      navigate(user?.account_role === 'admin' ? '/admin/dashboard' : '/', { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="auth-section">
      <div className="auth-card">
        <h1>Change password</h1>
        <p className="auth-subtitle">
          Signed in as <strong>{user?.account_username}</strong>. Choose a new password
          with at least 8 characters.
        </p>

        {error ? <div className="app-error">{error}</div> : null}

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="current_password">Current password</label>
            <input
              type="password"
              id="current_password"
              name="current_password"
              autoComplete="current-password"
              value={form.current_password}
              onChange={handleChange}
              required
              autoFocus
            />
          </div>

          <div className="field">
            <label htmlFor="new_password">New password</label>
            <input
              type="password"
              id="new_password"
              name="new_password"
              autoComplete="new-password"
              minLength={8}
              value={form.new_password}
              onChange={handleChange}
              required
            />
            <span className="hint">Minimum 8 characters</span>
          </div>

          <div className="field">
            <label htmlFor="confirm_password">Confirm new password</label>
            <input
              type="password"
              id="confirm_password"
              name="confirm_password"
              autoComplete="new-password"
              minLength={8}
              value={form.confirm_password}
              onChange={handleChange}
              required
            />
          </div>

          <button type="submit" className="btn btn-primary btn-block" disabled={busy}>
            {busy ? 'Updating...' : 'Update password'}
          </button>
        </form>

        <div className="auth-footer">
          <p>
            <Link to="/">Back to homepage</Link>
          </p>
        </div>
      </div>
    </section>
  )
}
