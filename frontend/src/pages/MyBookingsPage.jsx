import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import PageHero from '../components/PageHero'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { apiRequest } from '../lib/api'
import {
  ONLINE_PAYMENT_METHODS,
  formatDate,
  formatMoney,
  formatTime,
  paymentLabel,
  statusLabel,
} from '../lib/format'

export default function MyBookingsPage() {
  const { token } = useAuth()
  const { notify } = useToast()
  const [bookings, setBookings] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [cancelling, setCancelling] = useState(null)

  const loadBookings = useCallback(() => {
    apiRequest('/bookings', { token })
      .then((result) => {
        setBookings(result.data.bookings || [])
        setError('')
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [token])

  useEffect(() => {
    loadBookings()
  }, [loadBookings])

  const handleCancel = async (booking) => {
    if (!window.confirm('Cancel this booking?')) return
    setCancelling(booking.booking_id)
    try {
      const result = await apiRequest(`/bookings/${booking.booking_id}/cancel`, {
        method: 'POST',
        token,
      })
      notify(result.message || 'Booking cancelled.', 'info')
      loadBookings()
    } catch (err) {
      notify(err.message, 'error')
    } finally {
      setCancelling(null)
    }
  }

  return (
    <>
      <PageHero title="My Bookings" subtitle="Track and manage all your car wash appointments." />

      <section className="section">
        <div className="container">
          <div className="bookings-header">
            <h2>Your appointments</h2>
            <Link className="btn btn-primary" to="/services">
              Book new service
            </Link>
          </div>

          {error ? <div className="app-error">{error}</div> : null}
          {loading ? <div className="app-loading">Loading bookings...</div> : null}

          {!loading && bookings.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">&#128197;</div>
              <h3>No bookings yet</h3>
              <p>
                You haven&apos;t booked a service yet. Your next clean car is one click
                away.
              </p>
              <Link className="btn btn-primary" to="/services">
                Book your first service
              </Link>
            </div>
          ) : null}

          {bookings.length > 0 ? (
            <div className="booking-list">
              {bookings.map((booking) => {
                const canPay =
                  booking.payment_status !== 'paid' &&
                  ONLINE_PAYMENT_METHODS.includes(booking.payment_method) &&
                  booking.status !== 'cancelled'
                const canCancel = ['pending', 'confirmed'].includes(booking.status)
                return (
                  <article className="booking-card" key={booking.booking_id}>
                    <div className="booking-top">
                      <div>
                        <h3>{booking.service_name}</h3>
                        <span className={`status status-${booking.status}`}>
                          {statusLabel(booking.status)}
                        </span>
                        <span
                          className={`status status-${booking.payment_status === 'paid' ? 'completed' : 'pending'}`}
                        >
                          {booking.payment_status === 'paid' ? 'Paid' : 'Unpaid'}
                        </span>
                      </div>
                      <div className="booking-price">&#8369;{formatMoney(booking.price)}</div>
                    </div>

                    <div className="booking-grid">
                      <div>
                        <span>Date</span>
                        <strong>{formatDate(booking.booking_date)}</strong>
                      </div>
                      <div>
                        <span>Time</span>
                        <strong>{formatTime(booking.booking_time)}</strong>
                      </div>
                      <div>
                        <span>Vehicle</span>
                        <strong>{booking.vehicle_type}</strong>
                      </div>
                      <div>
                        <span>Customer</span>
                        <strong>{booking.customer_name}</strong>
                      </div>
                      <div>
                        <span>Payment</span>
                        <strong>{paymentLabel(booking.payment_method)}</strong>
                        {booking.payment_reference ? (
                          <small className="cell-muted">{booking.payment_reference}</small>
                        ) : null}
                      </div>
                    </div>

                    {booking.notes ? (
                      <div className="booking-notes">
                        <strong>Notes:</strong> {booking.notes}
                      </div>
                    ) : null}

                    {canPay || canCancel ? (
                      <div className="booking-actions">
                        {canPay ? (
                          <Link
                            className="btn btn-primary btn-sm"
                            to={`/payment/${booking.booking_id}`}
                          >
                            Pay now
                          </Link>
                        ) : null}
                        {canCancel ? (
                          <button
                            type="button"
                            className="btn btn-danger btn-sm"
                            onClick={() => handleCancel(booking)}
                            disabled={cancelling === booking.booking_id}
                          >
                            {cancelling === booking.booking_id ? 'Cancelling...' : 'Cancel booking'}
                          </button>
                        ) : null}
                      </div>
                    ) : null}
                  </article>
                )
              })}
            </div>
          ) : null}
        </div>
      </section>
    </>
  )
}
