import { useEffect, useRef, useState } from 'react'
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'

export default function Layout() {
  const { user, signOut } = useAuth()
  const { notify } = useToast()
  const location = useLocation()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const userMenuRef = useRef(null)

  useEffect(() => {
    setMenuOpen(false)
  }, [location.pathname])

  useEffect(() => {
    const onDocumentClick = (event) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target)) {
        userMenuRef.current.removeAttribute('open')
      }
    }
    document.addEventListener('click', onDocumentClick)
    return () => document.removeEventListener('click', onDocumentClick)
  }, [])

  const isActive = (path) => location.pathname === path

  const handleLogout = () => {
    signOut()
    notify('You have been logged out.', 'info')
    navigate('/')
  }

  return (
    <>
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>

      <header className="site-header">
        <div className="header-inner">
          <Link className="logo" to="/">
            Nice Day <span>Carwash</span>
          </Link>

          <button
            className="menu-toggle"
            type="button"
            aria-label="Toggle navigation"
            aria-expanded={menuOpen}
            aria-controls="siteNav"
            onClick={() => setMenuOpen((open) => !open)}
          >
            &#9776;
          </button>

          <nav className={`site-nav${menuOpen ? ' open' : ''}`} id="siteNav" aria-label="Main navigation">
            <Link className={isActive('/') ? 'active' : ''} to="/" aria-current={isActive('/') ? 'page' : undefined}>
              Home
            </Link>
            <Link className={isActive('/about') ? 'active' : ''} to="/about" aria-current={isActive('/about') ? 'page' : undefined}>
              About
            </Link>
            <Link
              className={isActive('/services') ? 'active' : ''}
              to="/services"
              aria-current={isActive('/services') ? 'page' : undefined}
            >
              Services
            </Link>
          </nav>

          <div className="header-actions">
            {user ? (
              <details className="user-menu" ref={userMenuRef}>
                <summary>{user.account_username}</summary>
                <div className="user-menu-panel">
                  {user.account_role === 'admin' ? (
                    <Link to="/admin/dashboard">Admin dashboard</Link>
                  ) : (
                    <>
                      <Link to="/my-bookings">My bookings</Link>
                      <Link to="/services">Book a service</Link>
                    </>
                  )}
                  <Link to="/change-password">Change password</Link>
                  <button type="button" className="logout-link" onClick={handleLogout}>
                    Log out
                  </button>
                </div>
              </details>
            ) : (
              <Link className="btn btn-primary btn-sm" to="/login">
                Login
              </Link>
            )}
          </div>
        </div>
      </header>

      <main className="site-main" id="main-content">
        <Outlet />
      </main>

      <footer className="site-footer">
        <div className="footer-inner">
          <div className="footer-brand">
            <Link className="logo logo-light" to="/">
              Nice Day <span>Carwash</span>
            </Link>
            <p>Premium, eco-friendly car care in Iloilo City.</p>
          </div>
          <div className="footer-col">
            <h3>Explore</h3>
            <Link to="/">Home</Link>
            <Link to="/about">About</Link>
            <Link to="/services">Services</Link>
          </div>
          <div className="footer-col">
            <h3>Contact</h3>
            <p>Lopez Jaena St, Jaro</p>
            <p>0927 457 6796</p>
            <p>nicedaycarwashiloilo@gmail.com</p>
          </div>
        </div>
        <div className="footer-bottom">
          &copy; {new Date().getFullYear()} Nice Day Carwash &middot; Iloilo City
        </div>
      </footer>
    </>
  )
}
