import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { apiRequest } from '../lib/api'

export default function RegisterPage() {
  const { signIn } = useAuth()
  const { notify } = useToast()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    full_name: '',
    username: '',
    email: '',
    phone: '',
    password: '',
    confirm_password: '',
  })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [match, setMatch] = useState({ ok: false, text: '' })

  useEffect(() => {
    if (form.confirm_password === '') {
      setMatch({ ok: false, text: '' })
      return
    }
    if (form.password === form.confirm_password) {
      setMatch({ ok: true, text: 'Passwords match' })
    } else {
      setMatch({ ok: false, text: 'Passwords do not match' })
    }
  }, [form.password, form.confirm_password])

  const handleChange = (event) => {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    if (form.password.length < 6) {
      setError('Password must be at least 6 characters long.')
      return
    }
    if (form.password !== form.confirm_password) {
      setError('Passwords do not match. Please check and try again.')
      return
    }
    setBusy(true)
    try {
      const result = await apiRequest('/auth/register', {
        method: 'POST',
        body: {
          full_name: form.full_name,
          username: form.username,
          email: form.email,
          phone: form.phone,
          password: form.password,
          confirm_password: form.confirm_password,
        },
      })
      signIn(result.data)
      notify(result.message || 'Registration successful.', 'success')
      navigate('/', { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="auth-section">
      <div className="auth-card auth-card-wide">
        <h1>Create an account</h1>
        <p className="auth-subtitle">Join Nice Day Carwash and book in seconds.</p>

        {error ? <div className="app-error">{error}</div> : null}

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="form-row">
            <div className="field">
              <label htmlFor="full_name">Full name</label>
              <input
                type="text"
                id="full_name"
                name="full_name"
                autoComplete="name"
                value={form.full_name}
                onChange={handleChange}
                required
              />
            </div>
            <div className="field">
              <label htmlFor="username">Username</label>
              <input
                type="text"
                id="username"
                name="username"
                autoComplete="username"
                minLength={3}
                value={form.username}
                onChange={handleChange}
                required
              />
            </div>
          </div>

          <div className="form-row">
            <div className="field">
              <label htmlFor="email">Email</label>
              <input
                type="email"
                id="email"
                name="email"
                autoComplete="email"
                value={form.email}
                onChange={handleChange}
                required
              />
            </div>
            <div className="field">
              <label htmlFor="phone">
                Phone <span className="hint">optional</span>
              </label>
              <input
                type="tel"
                id="phone"
                name="phone"
                autoComplete="tel"
                value={form.phone}
                onChange={handleChange}
              />
            </div>
          </div>

          <div className="form-row">
            <div className="field">
              <label htmlFor="password">Password</label>
              <input
                type="password"
                id="password"
                name="password"
                autoComplete="new-password"
                minLength={6}
                value={form.password}
                onChange={handleChange}
                className={match.text && !match.ok && form.confirm_password ? 'input-error' : match.ok ? 'input-success' : ''}
                required
              />
              <span className="hint">Minimum 6 characters</span>
            </div>
            <div className="field">
              <label htmlFor="confirm_password">Confirm password</label>
              <input
                type="password"
                id="confirm_password"
                name="confirm_password"
                autoComplete="new-password"
                value={form.confirm_password}
                onChange={handleChange}
                className={match.text && !match.ok ? 'input-error' : match.ok ? 'input-success' : ''}
                required
              />
              <span className={`hint ${match.ok ? 'match' : match.text ? 'no-match' : ''}`}>
                {match.text}
              </span>
            </div>
          </div>

          <button type="submit" className="btn btn-primary btn-block" disabled={busy || (form.confirm_password !== '' && !match.ok)}>
            {busy ? 'Creating account...' : 'Create account'}
          </button>
        </form>

        <div className="auth-footer">
          <p>
            Already have an account? <Link to="/login">Sign in here</Link>
          </p>
        </div>
        </div>
    </section>
  )
}
