import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { apiRequest } from '../lib/api'

export default function AdminLoginPage() {
  const { signIn } = useAuth()
  const { notify } = useToast()
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: '', password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const handleChange = (event) => {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      const result = await apiRequest('/auth/login', {
        method: 'POST',
        body: {
          username: form.username,
          password: form.password,
          admin_only: true,
        },
      })
      const session = result?.data
      if (!session?.user || session.user.account_role !== 'admin') {
        throw new Error('The server did not return a valid admin session. Please try again.')
      }
      signIn(session)
      notify('Admin signed in successfully.', 'success')
      navigate('/admin/dashboard', { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="auth-section">
      <div className="auth-card">
        <span className="auth-badge">Admin</span>
        <h1>Admin portal</h1>
        <p className="auth-subtitle">Sign in with an administrator account.</p>

        {error ? <div className="app-error">{error}</div> : null}

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="admin-username">Admin username</label>
            <input
              type="text"
              id="admin-username"
              name="username"
              autoComplete="username"
              value={form.username}
              onChange={handleChange}
              required
              autoFocus
            />
          </div>

          <div className="field">
            <label htmlFor="admin-password">Admin password</label>
            <input
              type="password"
              id="admin-password"
              name="password"
              autoComplete="current-password"
              value={form.password}
              onChange={handleChange}
              required
            />
          </div>

          <button type="submit" className="btn btn-primary btn-block" disabled={busy}>
            {busy ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        <div className="auth-footer">
          <p>
            Are you a client? <Link to="/login">Client login</Link>
          </p>
          <p className="auth-muted">
            <Link to="/">Back to homepage</Link>
          </p>
        </div>
      </div>
    </section>
  )
}
