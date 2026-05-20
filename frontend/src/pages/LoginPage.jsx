import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import LoginForm from '@/components/LoginForm'
import { login } from '@/api/auth'
import { setToken } from '@/lib/auth'

export default function LoginPage() {
  const navigate = useNavigate()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [serverError, setServerError] = useState('')

  async function handleSubmit(credentials) {
    setIsSubmitting(true)
    setServerError('')
    try {
      const { access_token } = await login(credentials)
      setToken(access_token)
      navigate('/dashboard', { replace: true })
    } catch (err) {
      const detail = err?.response?.data?.detail
      setServerError(detail || 'Something went wrong. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-muted/40 px-4">
      <div className="w-full max-w-sm space-y-6 rounded-xl border bg-card p-8 shadow-sm">
        <div className="space-y-1 text-center">
          <h1 className="text-2xl font-semibold tracking-tight">Sign in</h1>
          <p className="text-sm text-muted-foreground">
            Salary Management Tool
          </p>
        </div>
        <LoginForm
          onSubmit={handleSubmit}
          isSubmitting={isSubmitting}
          serverError={serverError}
        />
      </div>
    </main>
  )
}
