import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function ProtectedRoute({ role, children }) {
  const { user } = useAuth()
  const location = useLocation()

  if (!user) {
    const loginPath = role === 'admin' ? '/admin/login' : '/login'
    return <Navigate to={loginPath} state={{ from: location.pathname }} replace />
  }

  if (role && user.account_role !== role) {
    const fallback = user.account_role === 'admin' ? '/admin/dashboard' : '/'
    return <Navigate to={fallback} replace />
  }

  return children
}
