import { Navigate } from 'react-router-dom'
import { useAuth } from '@/lib/AuthContext'

export default function ProtectedRoute({ children, role }) {
  const { user, status } = useAuth()

  if (status === 'anonymous') {
    return <Navigate to="/login" replace />
  }

  if (status === 'loading') {
    return null
  }

  if (role && user?.role !== role) {
    return <Navigate to="/dashboard" replace />
  }

  return children
}
