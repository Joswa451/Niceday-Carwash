import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function HomePage() {
  const { user } = useAuth()

  return (
    <>
      <section className="hero">
        <div className="hero-inner">
          <span className="eyebrow">Iloilo City&apos;s trusted car wash</span>
          <h1>
            Premium car care,
            <br />
            made simple.
          </h1>
          <p>
            Professional, eco-friendly cleaning that keeps your vehicle looking its
            best - without the wait.
          </p>
          <div className="hero-actions">
            <Link className="btn btn-primary btn-lg" to="/services">
              Book a wash
            </Link>
            <Link className="btn btn-ghost btn-lg" to="/about">
              Learn more
            </Link>
          </div>
          <div className="hero-stats">
            <div>
              <strong>30 min</strong>
              <span>Average wash</span>
            </div>
            <div>
              <strong>100%</strong>
              <span>Eco-friendly products</span>
            </div>
            <div>
              <strong>4.9/5</strong>
              <span>Customer rating</span>
            </div>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <div className="feature-grid">
            <article className="feature-card">
              <div className="feature-icon">&#9889;</div>
              <h3>Fast service</h3>
              <p>
                Most washes are finished in 30 to 60 minutes so you can get back on
                the road.
              </p>
            </article>
            <article className="feature-card">
              <div className="feature-icon">&#127793;</div>
              <h3>Eco-friendly</h3>
              <p>
                Biodegradable products and water-saving methods that are kinder to the
                planet.
              </p>
            </article>
            <article className="feature-card">
              <div className="feature-icon">&#128737;</div>
              <h3>Quality assured</h3>
              <p>
                Trained specialists and a satisfaction guarantee on every single
                service.
              </p>
            </article>
          </div>
        </div>
      </section>

      <section className="section section-alt">
        <div className="container">
          <div className="section-heading">
            <h2>Booking takes less than a minute</h2>
            <p>Pick a package, choose a time, and leave the rest to us.</p>
          </div>
          <div className="steps-grid">
            <article className="step-card">
              <span className="step-number">1</span>
              <h3>Choose a service</h3>
              <p>
                Browse our wash and detail packages and pick the one that fits your
                vehicle.
              </p>
            </article>
            <article className="step-card">
              <span className="step-number">2</span>
              <h3>Pick a schedule</h3>
              <p>
                Select a date and time that works for you. We are open from 6 AM to
                6 PM.
              </p>
            </article>
            <article className="step-card">
              <span className="step-number">3</span>
              <h3>Pay your way</h3>
              <p>
                Pay with cash at the counter, or complete your payment online with
                GCash, Maya, or bank transfer.
              </p>
            </article>
          </div>
          <div className="section-cta">
            <Link className="btn btn-primary btn-lg" to="/services">
              Book a wash now
            </Link>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <div className="cta-panel">
            <div>
              <h2>Ready for a nicer day?</h2>
              <p>
                Create an account to book, track, and pay for your car wash
                appointments online.
              </p>
            </div>
            <div className="cta-actions">
              {user ? (
                <Link className="btn btn-light btn-lg" to="/services">
                  Book a service
                </Link>
              ) : (
                <>
                  <Link className="btn btn-light btn-lg" to="/register">
                    Create an account
                  </Link>
                  <Link className="btn btn-ghost btn-lg" to="/login">
                    Sign in
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      </section>
    </>
  )
}
