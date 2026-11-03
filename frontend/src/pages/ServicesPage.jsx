import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import PageHero from '../components/PageHero'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { apiRequest } from '../lib/api'
import { formatMoney, todayInputValue } from '../lib/format'

const ICONS = ['\u{1F6BF}', '\u2728', '\u{1F48E}', '\u{1F527}', '\u{1F697}', '\u{1F33F}']

const PAYMENT_METHODS = [
  { value: 'cash', label: 'Cash' },
  { value: 'gcash', label: 'GCash' },
  { value: 'maya', label: 'Maya' },
  { value: 'bank_transfer', label: 'Bank Transfer' },
]

const TIMES = [
  ['06:00', '6:00 AM'],
  ['07:00', '7:00 AM'],
  ['08:00', '8:00 AM'],
  ['09:00', '9:00 AM'],
  ['10:00', '10:00 AM'],
  ['11:00', '11:00 AM'],
  ['12:00', '12:00 PM'],
  ['13:00', '1:00 PM'],
  ['14:00', '2:00 PM'],
  ['15:00', '3:00 PM'],
  ['16:00', '4:00 PM'],
  ['17:00', '5:00 PM'],
  ['18:00', '6:00 PM'],
]

const ONLINE_METHODS = ['gcash', 'maya', 'bank_transfer']

export default function ServicesPage() {
  const { user, token } = useAuth()
  const { notify } = useToast()
  const navigate = useNavigate()
  const [services, setServices] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState(null)
  const [form, setForm] = useState({
    booking_date: todayInputValue(),
    booking_time: '',
    customer_name: '',
    customer_phone: '',
    vehicle_type: '',
    payment_method: 'cash',
    notes: '',
  })
  const [bookingError, setBookingError] = useState('')
  const [bookingBusy, setBookingBusy] = useState(false)

  useEffect(() => {
    let active = true
    apiRequest('/services')
      .then((result) => {
        if (active) setServices(result.data.services || [])
      })
      .catch((err) => {
        if (active) setError(err.message)
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    if (!selected) return undefined
    const onKeyDown = (event) => {
      if (event.key === 'Escape') closeModal()
    }
    document.body.classList.add('modal-open')
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.body.classList.remove('modal-open')
      document.removeEventListener('keydown', onKeyDown)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected])

  const openModal = (service) => {
    setSelected(service)
    setBookingError('')
    setForm({
      booking_date: todayInputValue(),
      booking_time: '',
      customer_name: user?.full_name || '',
      customer_phone: user?.phone || '',
      vehicle_type: '',
      payment_method: 'cash',
      notes: '',
    })
  }

  const closeModal = () => setSelected(null)

  const handleChange = (event) => {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setBookingError('')
    setBookingBusy(true)
    try {
      const result = await apiRequest('/bookings', {
        method: 'POST',
        token,
        body: {
          service_id: selected.service_id,
          booking_date: form.booking_date,
          booking_time: form.booking_time,
          customer_name: form.customer_name,
          customer_phone: form.customer_phone,
          vehicle_type: form.vehicle_type,
          payment_method: form.payment_method,
          notes: form.notes,
        },
      })
      const booking = result.data.booking
      notify(result.message || 'Booking created successfully.', 'success')
      closeModal()
      if (ONLINE_METHODS.includes(form.payment_method)) {
        navigate(`/payment/${booking.booking_id}`)
      } else {
        navigate('/my-bookings')
      }
    } catch (err) {
      setBookingError(err.message)
    } finally {
      setBookingBusy(false)
    }
  }

  return (
    <>
      <PageHero
        title="Our Services"
        subtitle="Professional car care packages tailored to your vehicle."
      />

      <section className="section">
        <div className="container">
          <div className="section-heading">
            <h2>Choose your package</h2>
            <p>From a quick express wash to a full premium detail.</p>
          </div>

          {error ? <div className="app-error">{error}</div> : null}
          {loading ? <div className="app-loading">Loading services...</div> : null}

          {!loading && services.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">&#128295;</div>
              <h3>No services available yet</h3>
              <p>Please check back soon.</p>
            </div>
          ) : null}

          {services.length > 0 ? (
            <div className="service-grid">
              {services.map((service, index) => (
                <article className="service-card" key={service.service_id}>
                  <div className="service-icon">{ICONS[index % ICONS.length]}</div>
                  <div className="service-title-row">
                    <h3>{service.service_name}</h3>
                    <span className="service-duration">{service.duration_minutes} min</span>
                  </div>
                  <div className="price">&#8369;{formatMoney(service.price)}</div>
                  {service.service_description ? (
                    <p className="service-desc">{service.service_description}</p>
                  ) : null}
                  {user?.account_role === 'client' ? (
                    <button
                      className="btn btn-primary service-btn"
                      type="button"
                      onClick={() => openModal(service)}
                    >
                      Book now
                    </button>
                  ) : user?.account_role === 'admin' ? (
                    <Link className="btn btn-outline service-btn" to="/admin/dashboard">
                      Admin account
                    </Link>
                  ) : (
                    <Link className="btn btn-outline service-btn" to="/login" state={{ from: '/services' }}>
                      Login to book
                    </Link>
                  )}
                </article>
              ))}
            </div>
          ) : null}
        </div>
      </section>

      <section className="section section-alt">
        <div className="container">
          <div className="section-heading">
            <h2>Additional services</h2>
            <p>Small extras that make a big difference.</p>
          </div>
          <div className="addon-grid">
            <div className="addon-item">
              <span className="addon-icon">&#129533;</span>
              <div>
                <h4>Headlight Restoration</h4>
                <p>&#8369;200 &middot; Restore clarity to foggy headlights</p>
              </div>
            </div>
            <div className="addon-item">
              <span className="addon-icon">&#128737;</span>
              <div>
                <h4>Paint Protection Film</h4>
                <p>&#8369;1,500 &middot; Ultimate paint protection</p>
              </div>
            </div>
            <div className="addon-item">
              <span className="addon-icon">&#10052;</span>
              <div>
                <h4>AC Cleaning</h4>
                <p>&#8369;300 &middot; Fresh and clean air system</p>
              </div>
            </div>
            <div className="addon-item">
              <span className="addon-icon">&#128269;</span>
              <div>
                <h4>Scratch Removal</h4>
                <p>&#8369;400 &middot; Professional scratch repair</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <div className="section-heading">
            <h2>Our guarantee</h2>
            <p>Simple promises we stand behind.</p>
          </div>
          <div className="guarantee-grid">
            <div className="guarantee-item">
              <div className="guarantee-icon">&#9889;</div>
              <h3>Fast service</h3>
              <p>Most services are completed within 30 to 60 minutes.</p>
            </div>
            <div className="guarantee-item">
              <div className="guarantee-icon">&#128175;</div>
              <h3>Quality assured</h3>
              <p>100% satisfaction guarantee or your money back.</p>
            </div>
            <div className="guarantee-item">
              <div className="guarantee-icon">&#127775;</div>
              <h3>Professional staff</h3>
              <p>Trained and certified car care specialists.</p>
            </div>
            <div className="guarantee-item">
              <div className="guarantee-icon">&#127793;</div>
              <h3>Eco-friendly</h3>
              <p>Environmentally responsible products and methods.</p>
            </div>
          </div>
        </div>
      </section>

      <div className={`modal${selected ? ' is-open' : ''}`} aria-hidden={selected ? 'false' : 'true'}>
        <div className="modal-card" role="dialog" aria-modal="true" aria-labelledby="bookingModalTitle">
          <button className="modal-close" type="button" aria-label="Close" onClick={closeModal}>
            &times;
          </button>
          <h2 id="bookingModalTitle">Book a service</h2>
          <p className="modal-subtitle">
            {selected ? `${selected.service_name} - \u20B1${formatMoney(selected.price)}` : ''}
          </p>

          {bookingError ? <div className="app-error">{bookingError}</div> : null}

          <form onSubmit={handleSubmit}>
            <div className="form-row">
              <div className="field">
                <label htmlFor="bookingDate">Date</label>
                <input
                  type="date"
                  id="bookingDate"
                  name="booking_date"
                  min={todayInputValue()}
                  value={form.booking_date}
                  onChange={handleChange}
                  required
                  autoFocus
                />
              </div>
              <div className="field">
                <label htmlFor="bookingTime">Time</label>
                <select
                  id="bookingTime"
                  name="booking_time"
                  value={form.booking_time}
                  onChange={handleChange}
                  required
                >
                  <option value="">Choose a time</option>
                  {TIMES.map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="field">
              <label htmlFor="customerName">Full name</label>
              <input
                type="text"
                id="customerName"
                name="customer_name"
                value={form.customer_name}
                onChange={handleChange}
                placeholder="Your full name"
                required
              />
            </div>

            <div className="form-row">
              <div className="field">
                <label htmlFor="customerPhone">
                  Phone <span className="hint">optional</span>
                </label>
                <input
                  type="tel"
                  id="customerPhone"
                  name="customer_phone"
                  value={form.customer_phone}
                  onChange={handleChange}
                  placeholder="Your phone number"
                />
              </div>
              <div className="field">
                <label htmlFor="vehicleType">Vehicle type</label>
                <input
                  type="text"
                  id="vehicleType"
                  name="vehicle_type"
                  value={form.vehicle_type}
                  onChange={handleChange}
                  placeholder="e.g. Toyota Camry"
                  required
                />
              </div>
            </div>

            <div className="field">
              <label htmlFor="paymentMethod">Payment method</label>
              <select
                id="paymentMethod"
                name="payment_method"
                value={form.payment_method}
                onChange={handleChange}
                required
              >
                {PAYMENT_METHODS.map((method) => (
                  <option key={method.value} value={method.value}>
                    {method.label}
                  </option>
                ))}
              </select>
              <span className="hint">
                {ONLINE_METHODS.includes(form.payment_method)
                  ? 'You can complete the payment right after booking.'
                  : 'Pay using cash when the booking is confirmed.'}
              </span>
            </div>

            <div className="field">
              <label htmlFor="notes">
                Notes <span className="hint">optional</span>
              </label>
              <textarea
                id="notes"
                name="notes"
                rows={3}
                value={form.notes}
                onChange={handleChange}
                placeholder="Anything we should know?"
              />
            </div>

            <div className="modal-actions">
              <button type="button" className="btn btn-outline" onClick={closeModal}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary" disabled={bookingBusy}>
                {bookingBusy ? 'Booking...' : 'Confirm booking'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  )
}
