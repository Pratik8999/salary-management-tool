import AppRoutes from '@/routes/AppRoutes'
import { AuthProvider } from '@/lib/AuthContext'

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}
