import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import PageHero from '../components/PageHero'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { apiRequest } from '../lib/api'
import {
  ONLINE_PAYMENT_METHODS,
  formatDate,
  formatDateTime,
  formatMoney,
  formatTime,
  paymentLabel,
  statusLabel,
} from '../lib/format'

export default function PaymentPage() {
  const { bookingId } = useParams()
  const { token } = useAuth()
  const { notify } = useToast()
  const [booking, setBooking] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const loadBooking = useCallback(() => {
    apiRequest(`/bookings/${bookingId}`, { token })
      .then((result) => {
        setBooking(result.data.booking)
        setError('')
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [bookingId, token])

  useEffect(() => {
    loadBooking()
  }, [loadBooking])

  const handlePay = async () => {
    setBusy(true)
    try {
      const result = await apiRequest(`/bookings/${bookingId}/pay`, {
        method: 'POST',
        token,
      })
      notify(result.message || 'Payment recorded successfully.', 'success')
      loadBooking()
    } catch (err) {
      notify(err.message, 'error')
    } finally {
      setBusy(false)
    }
  }

  const online = booking ? ONLINE_PAYMENT_METHODS.includes(booking.payment_method) : false

  return (
    <>
      <PageHero
        title="Complete your payment"
        subtitle="Review your booking and pay using your chosen method."
      />

      <section className="section">
        <div className="container">
          {error ? <div className="app-error">{error}</div> : null}
          {loading ? <div className="app-loading">Loading booking...</div> : null}

          {booking ? (
            <div className="booking-card">
              <div className="booking-top">
                <div>
                  <h3>{booking.service_name}</h3>
                  <span className={`status status-${booking.status}`}>
                    {statusLabel(booking.status)}
                  </span>
                </div>
                <div className="booking-price">&#8369;{formatMoney(booking.price)}</div>
              </div>

              <div className="booking-grid">
                <div>
                  <span>Booking</span>
                  <strong>#{booking.booking_id}</strong>
                </div>
                <div>
                  <span>Date</span>
                  <strong>{formatDate(booking.booking_date)}</strong>
                </div>
                <div>
                  <span>Time</span>
                  <strong>{formatTime(booking.booking_time)}</strong>
                </div>
                <div>
                  <span>Payment method</span>
                  <strong>{paymentLabel(booking.payment_method)}</strong>
                </div>
              </div>

              {booking.payment_status === 'paid' ? (
                <div className="payment-panel">
                  <span className="status status-completed">Paid</span>
                  <p>
                    Reference: <strong>{booking.payment_reference || 'N/A'}</strong>
                    <br />
                    Paid on {formatDateTime(booking.paid_at)}
                  </p>
                </div>
              ) : booking.status === 'cancelled' ? (
                <div className="payment-panel">
                  <span className="status status-cancelled">Cancelled</span>
                  <p>This booking was cancelled, so online payment is no longer available.</p>
                </div>
              ) : !online ? (
                <div className="payment-panel">
                  <span className="status status-pending">Pay at counter</span>
                  <p>
                    You chose to pay with cash. Please pay at the counter when you arrive
                    for your appointment.
                  </p>
                </div>
              ) : (
                <div className="payment-panel">
                  <span className="status status-pending">Unpaid</span>
                  <p>
                    You are about to pay <strong>&#8369;{formatMoney(booking.price)}</strong>{' '}
                    using {paymentLabel(booking.payment_method)}.
                  </p>
                  <p className="payment-note">
                    Demo checkout: clicking the button below records this booking as paid.
                    No real money is charged until a payment gateway is connected.
                  </p>
                  <button type="button" className="btn btn-primary" onClick={handlePay} disabled={busy}>
                    {busy ? 'Processing...' : `Pay \u20B1${formatMoney(booking.price)} now`}
                  </button>
                </div>
              )}

              <div className="booking-actions">
                <Link className="btn btn-outline" to="/my-bookings">
                  Back to my bookings
                </Link>
              </div>
            </div>
          ) : null}
        </div>
      </section>
    </>
  )
}
