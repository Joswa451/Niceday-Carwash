import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { apiRequest } from '../lib/api'
import {
  formatDate,
  formatMoney,
  formatTime,
  paymentLabel,
  statusLabel,
} from '../lib/format'

const STATUS_OPTIONS = ['pending', 'confirmed', 'in_progress', 'completed', 'cancelled']

const TABS = [
  ['bookings', 'Bookings'],
  ['services', 'Services'],
  ['accounts', 'Accounts'],
  ['reports', 'Reports'],
]

function AdminBookingRow({ booking, onUpdateStatus, onMarkPaid }) {
  const [status, setStatus] = useState(booking.status)

  useEffect(() => {
    setStatus(booking.status)
  }, [booking.status])

  return (
    <tr>
      <td>#{booking.booking_id}</td>
      <td>{booking.client_name}</td>
      <td>
        {booking.service_name}
        <span className="cell-muted">&#8369;{formatMoney(booking.price)}</span>
      </td>
      <td>{booking.customer_name}</td>
      <td>{booking.vehicle_type}</td>
      <td>
        {formatDate(booking.booking_date)}
        <span className="cell-muted">{formatTime(booking.booking_time)}</span>
      </td>
      <td>
        {paymentLabel(booking.payment_method)}
        <span className="cell-muted">
          {booking.payment_status === 'paid' ? 'Paid' : 'Unpaid'}
          {booking.payment_reference ? ` \u00B7 ${booking.payment_reference}` : ''}
        </span>
      </td>
      <td>
        <span className={`status status-${booking.status}`}>{statusLabel(booking.status)}</span>
      </td>
      <td>
        <div className="row-actions">
          <div className="inline-form">
            <select
              className="status-select"
              aria-label={`Status for booking ${booking.booking_id}`}
              value={status}
              onChange={(event) => setStatus(event.target.value)}
            >
              {STATUS_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {statusLabel(option)}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="btn btn-outline btn-sm"
              disabled={status === booking.status}
              onClick={() => onUpdateStatus(booking.booking_id, status)}
            >
              Save
            </button>
          </div>
          {booking.payment_status !== 'paid' && booking.status !== 'cancelled' ? (
            <button
              type="button"
              className="btn btn-outline btn-sm"
              onClick={() => onMarkPaid(booking.booking_id)}
            >
              Mark paid
            </button>
          ) : null}
        </div>
      </td>
    </tr>
  )
}

export default function AdminDashboardPage() {
  const { user, token, signOut } = useAuth()
  const { notify } = useToast()
  const navigate = useNavigate()
  const location = useLocation()
  const initialTab = TABS.some(([key]) => `#${key}` === location.hash)
    ? location.hash.slice(1)
    : 'bookings'
  const [tab, setTab] = useState(initialTab)
  const [data, setData] = useState({ bookings: [], services: [], accounts: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')

  const [serviceForm, setServiceForm] = useState({
    service_name: '',
    price: '',
    duration_minutes: '',
    service_description: '',
  })
  const [accountForm, setAccountForm] = useState({
    username_inp: '',
    password_inp: '',
    role_inp: '',
    email_inp: '',
  })
  const [busy, setBusy] = useState(false)

  const loadDashboard = useCallback(() => {
    apiRequest('/admin/dashboard', { token })
      .then((result) => {
        setData({
          bookings: Array.isArray(result?.data?.bookings) ? result.data.bookings : [],
          services: Array.isArray(result?.data?.services) ? result.data.services : [],
          accounts: Array.isArray(result?.data?.accounts) ? result.data.accounts : [],
        })
        setError('')
      })
      .catch((err) => {
        setError(err.message)
        if (err.status === 401) {
          signOut()
          navigate('/admin/login', { replace: true })
        }
      })
      .finally(() => setLoading(false))
  }, [token, signOut, navigate])

  useEffect(() => {
    loadDashboard()
  }, [loadDashboard])

  const openTab = (key) => {
    setTab(key)
    window.history.replaceState(null, '', `#${key}`)
  }

  const counts = useMemo(() => {
    const bookings = data.bookings
    return {
      total: bookings.length,
      pending: bookings.filter((item) => item.status === 'pending').length,
      confirmed: bookings.filter((item) => item.status === 'confirmed').length,
      completed: bookings.filter((item) => item.status === 'completed').length,
      admins: data.accounts.filter((item) => item.account_role === 'admin').length,
      clients: data.accounts.filter((item) => item.account_role === 'client').length,
      revenue: bookings
        .filter((item) => item.status === 'completed')
        .reduce((sum, item) => sum + Number(item.price || 0), 0),
    }
  }, [data])

  const filteredBookings = useMemo(() => {
    const query = search.trim().toLowerCase()
    return data.bookings.filter((booking) => {
      const matchesStatus = !statusFilter || booking.status === statusFilter
      if (!matchesStatus) return false
      if (!query) return true
      const haystack = [
        booking.booking_id,
        booking.client_name,
        booking.customer_name,
        booking.vehicle_type,
        booking.service_name,
      ]
        .join(' ')
        .toLowerCase()
      return haystack.includes(query)
    })
  }, [data.bookings, search, statusFilter])

  const runAction = async (action, successMessage) => {
    setBusy(true)
    try {
      const result = await action()
      notify(result?.message || successMessage, 'success')
      loadDashboard()
      return true
    } catch (err) {
      notify(err.message, 'error')
      return false
    } finally {
      setBusy(false)
    }
  }

  const updateStatus = (bookingId, status) =>
    runAction(
      () =>
        apiRequest(`/bookings/${bookingId}/status`, {
          method: 'PATCH',
          token,
          body: { status },
        }),
      'Booking status updated.',
    )

  const markPaid = (bookingId) =>
    runAction(
      () => apiRequest(`/bookings/${bookingId}/mark-paid`, { method: 'POST', token }),
      'Booking marked as paid.',
    )

  const handleServiceChange = (event) => {
    setServiceForm((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  const addService = (event) => {
    event.preventDefault()
    runAction(
      () =>
        apiRequest('/admin/services', {
          method: 'POST',
          token,
          body: {
            service_name: serviceForm.service_name,
            price: serviceForm.price,
            duration_minutes: serviceForm.duration_minutes,
            service_description: serviceForm.service_description,
          },
        }),
      'Service added.',
    ).then((ok) => {
      if (ok) {
        setServiceForm({
          service_name: '',
          price: '',
          duration_minutes: '',
          service_description: '',
        })
      }
    })
  }

  const handleAccountChange = (event) => {
    setAccountForm((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  const addAccount = (event) => {
    event.preventDefault()
    runAction(
      () =>
        apiRequest('/admin/accounts', {
          method: 'POST',
          token,
          body: {
            username_inp: accountForm.username_inp,
            password_inp: accountForm.password_inp,
            role_inp: accountForm.role_inp,
            email_inp: accountForm.email_inp,
          },
        }),
      'Account created.',
    ).then((ok) => {
      if (ok) {
        setAccountForm({ username_inp: '', password_inp: '', role_inp: '', email_inp: '' })
      }
    })
  }

  const handleLogout = () => {
    signOut()
    notify('You have been logged out.', 'info')
    navigate('/')
  }

  return (
    <div className="admin-shell admin-dashboard-wrap">
      <header className="admin-header">
        <div className="admin-header-inner">
          <Link className="logo logo-light" to="/">
            Nice Day <span>Carwash</span>
          </Link>
          <div className="admin-user">
            <span>
              Signed in as <strong>{user?.account_username}</strong>
            </span>
            <Link className="btn btn-ghost btn-sm" to="/">
              View site
            </Link>
            <Link className="btn btn-ghost btn-sm" to="/change-password">
              Change password
            </Link>
            <button type="button" className="btn btn-light btn-sm admin-logout" onClick={handleLogout}>
              Log out
            </button>
          </div>
        </div>
      </header>

      <nav className="admin-nav">
        <div className="admin-nav-inner">
          {TABS.map(([key, label]) => (
            <a
              key={key}
              href={`#${key}`}
              className={`tab-link${tab === key ? ' active' : ''}`}
              onClick={(event) => {
                event.preventDefault()
                openTab(key)
              }}
            >
              {label}
            </a>
          ))}
        </div>
      </nav>

      <main className="admin-main">
        {error ? <div className="app-error">{error}</div> : null}
        {loading ? <div className="app-loading">Loading dashboard...</div> : null}

        <section className={`tab-content${tab === 'bookings' ? ' active' : ''}`}>
          <div className="section-heading">
            <h1>Bookings</h1>
            <p>Review and update every customer appointment.</p>
          </div>

          <div className="stats-grid">
            <div className="stat-card">
              <span>Total bookings</span>
              <strong>{counts.total}</strong>
            </div>
            <div className="stat-card warning">
              <span>Pending</span>
              <strong>{counts.pending}</strong>
            </div>
            <div className="stat-card info">
              <span>Confirmed</span>
              <strong>{counts.confirmed}</strong>
            </div>
            <div className="stat-card success">
              <span>Completed</span>
              <strong>{counts.completed}</strong>
            </div>
          </div>

          {data.bookings.length > 0 ? (
            <>
              <div className="table-toolbar">
                <div className="field toolbar-search">
                  <label className="sr-only" htmlFor="bookingSearch">
                    Search bookings
                  </label>
                  <input
                    type="search"
                    id="bookingSearch"
                    placeholder="Search by client, customer, vehicle, service, or ID"
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                  />
                </div>
                <div className="field toolbar-filter">
                  <label htmlFor="bookingStatusFilter">Status</label>
                  <select
                    id="bookingStatusFilter"
                    value={statusFilter}
                    onChange={(event) => setStatusFilter(event.target.value)}
                  >
                    <option value="">All statuses</option>
                    {STATUS_OPTIONS.map((option) => (
                      <option key={option} value={option}>
                        {statusLabel(option)}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Client</th>
                      <th>Service</th>
                      <th>Customer</th>
                      <th>Vehicle</th>
                      <th>Schedule</th>
                      <th>Payment</th>
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredBookings.map((booking) => (
                      <AdminBookingRow
                        key={booking.booking_id}
                        booking={booking}
                        onUpdateStatus={updateStatus}
                        onMarkPaid={markPaid}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
              {filteredBookings.length === 0 ? (
                <p className="cell-muted">No bookings match your filters.</p>
              ) : null}
            </>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">&#128197;</div>
              <h3>No bookings yet</h3>
              <p>New bookings will appear here automatically.</p>
            </div>
          )}
        </section>

        <section className={`tab-content${tab === 'services' ? ' active' : ''}`}>
          <div className="section-heading">
            <h1>Services</h1>
            <p>Manage the packages customers can book.</p>
          </div>

          <div className="panel">
            <h2>Add a new service</h2>
            <form onSubmit={addService}>
              <div className="form-row">
                <div className="field">
                  <label htmlFor="service_name">Service name</label>
                  <input
                    type="text"
                    id="service_name"
                    name="service_name"
                    value={serviceForm.service_name}
                    onChange={handleServiceChange}
                    required
                  />
                </div>
                <div className="field">
                  <label htmlFor="price">Price (&#8369;)</label>
                  <input
                    type="number"
                    id="price"
                    name="price"
                    step="0.01"
                    min="0.01"
                    value={serviceForm.price}
                    onChange={handleServiceChange}
                    required
                  />
                </div>
              </div>
              <div className="form-row">
                <div className="field">
                  <label htmlFor="duration_minutes">Duration (minutes)</label>
                  <input
                    type="number"
                    id="duration_minutes"
                    name="duration_minutes"
                    min="1"
                    value={serviceForm.duration_minutes}
                    onChange={handleServiceChange}
                    required
                  />
                </div>
                <div className="field">
                  <label htmlFor="service_description">Description</label>
                  <input
                    type="text"
                    id="service_description"
                    name="service_description"
                    value={serviceForm.service_description}
                    onChange={handleServiceChange}
                  />
                </div>
              </div>
              <button type="submit" className="btn btn-primary" disabled={busy}>
                Add service
              </button>
            </form>
          </div>

          {data.services.length > 0 ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Description</th>
                    <th>Price</th>
                    <th>Duration</th>
                    <th>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {data.services.map((service) => (
                    <tr key={service.service_id}>
                      <td>#{service.service_id}</td>
                      <td>{service.service_name}</td>
                      <td>{service.service_description || '-'}</td>
                      <td>&#8369;{formatMoney(service.price)}</td>
                      <td>{service.duration_minutes} min</td>
                      <td>{formatDate(service.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">&#128295;</div>
              <h3>No services yet</h3>
              <p>Add your first service using the form above.</p>
            </div>
          )}
        </section>

        <section className={`tab-content${tab === 'accounts' ? ' active' : ''}`}>
          <div className="section-heading">
            <h1>Accounts</h1>
            <p>Manage client and administrator accounts.</p>
          </div>

          <div className="stats-grid">
            <div className="stat-card">
              <span>Total accounts</span>
              <strong>{data.accounts.length}</strong>
            </div>
            <div className="stat-card info">
              <span>Admins</span>
              <strong>{counts.admins}</strong>
            </div>
            <div className="stat-card success">
              <span>Clients</span>
              <strong>{counts.clients}</strong>
            </div>
          </div>

          <div className="panel">
            <h2>Create an account</h2>
            <form onSubmit={addAccount}>
              <div className="form-row">
                <div className="field">
                  <label htmlFor="username_inp">Username</label>
                  <input
                    type="text"
                    id="username_inp"
                    name="username_inp"
                    minLength={3}
                    value={accountForm.username_inp}
                    onChange={handleAccountChange}
                    required
                  />
                </div>
                <div className="field">
                  <label htmlFor="password_inp">Password</label>
                  <input
                    type="password"
                    id="password_inp"
                    name="password_inp"
                    minLength={6}
                    value={accountForm.password_inp}
                    onChange={handleAccountChange}
                    required
                  />
                </div>
              </div>
              <div className="form-row">
                <div className="field">
                  <label htmlFor="role_inp">Role</label>
                  <select
                    id="role_inp"
                    name="role_inp"
                    value={accountForm.role_inp}
                    onChange={handleAccountChange}
                    required
                  >
                    <option value="">Select role</option>
                    <option value="client">Client</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="email_inp">Email</label>
                  <input
                    type="email"
                    id="email_inp"
                    name="email_inp"
                    value={accountForm.email_inp}
                    onChange={handleAccountChange}
                    required
                  />
                </div>
              </div>
              <button type="submit" className="btn btn-primary" disabled={busy}>
                Create account
              </button>
            </form>
          </div>

          {data.accounts.length > 0 ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Username</th>
                    <th>Role</th>
                    <th>Email</th>
                    <th>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {data.accounts.map((account) => (
                    <tr key={account.account_id}>
                      <td>#{account.account_id}</td>
                      <td>{account.account_username}</td>
                      <td>
                        <span className={`role-badge role-${account.account_role}`}>
                          {statusLabel(account.account_role)}
                        </span>
                      </td>
                      <td>{account.account_email || '-'}</td>
                      <td>{formatDate(account.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">&#128100;</div>
              <h3>No accounts yet</h3>
              <p>Create the first account using the form above.</p>
            </div>
          )}
        </section>

        <section className={`tab-content${tab === 'reports' ? ' active' : ''}`}>
          <div className="section-heading">
            <h1>Reports</h1>
            <p>A quick snapshot of the business.</p>
          </div>

          <div className="stats-grid">
            <div className="stat-card">
              <span>Total bookings</span>
              <strong>{counts.total}</strong>
            </div>
            <div className="stat-card">
              <span>Services</span>
              <strong>{data.services.length}</strong>
            </div>
            <div className="stat-card">
              <span>Accounts</span>
              <strong>{data.accounts.length}</strong>
            </div>
            <div className="stat-card success">
              <span>Revenue (completed)</span>
              <strong>&#8369;{formatMoney(counts.revenue)}</strong>
            </div>
          </div>

          <div className="panel">
            <h2>Recent bookings</h2>
            {data.bookings.length > 0 ? (
              <ul className="activity-list">
                {data.bookings.slice(0, 5).map((booking) => (
                  <li className="activity-item" key={booking.booking_id}>
                    <div>
                      <strong>{booking.service_name}</strong>
                      <span className="cell-muted">by {booking.customer_name}</span>
                    </div>
                    <div className="activity-meta">
                      <span className={`status status-${booking.status}`}>
                        {statusLabel(booking.status)}
                      </span>
                      <span
                        className={`status status-${booking.payment_status === 'paid' ? 'completed' : 'pending'}`}
                      >
                        {booking.payment_status === 'paid' ? 'Paid' : 'Unpaid'}
                      </span>
                      <span>&#8369;{formatMoney(booking.price)}</span>
                      <span className="cell-muted">{formatDate(booking.created_at)}</span>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="cell-muted">No activity to show yet.</p>
            )}
          </div>
        </section>
      </main>
    </div>
  )
}
