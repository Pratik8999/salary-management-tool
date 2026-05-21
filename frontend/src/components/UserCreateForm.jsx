import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const MIN_PASSWORD_LENGTH = 8

function validate({ email, password }) {
  const errors = {}
  if (!email) errors.email = 'Email is required'
  else if (!EMAIL_RE.test(email)) errors.email = 'Enter a valid email'
  if (!password) errors.password = 'Password is required'
  else if (password.length < MIN_PASSWORD_LENGTH) {
    errors.password = `Password must be at least ${MIN_PASSWORD_LENGTH} characters`
  }
  return errors
}

export default function UserCreateForm({
  onSubmit,
  isSubmitting = false,
  serverError = '',
}) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('hr')
  const [errors, setErrors] = useState({})

  function handleSubmit(e) {
    e.preventDefault()
    const next = validate({ email, password })
    setErrors(next)
    if (Object.keys(next).length === 0) {
      onSubmit({ email, password, role })
    }
  }

  return (
    <form noValidate onSubmit={handleSubmit} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="space-y-1.5">
          <Label htmlFor="new-user-email">Email</Label>
          <Input
            id="new-user-email"
            type="email"
            autoComplete="off"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            aria-invalid={Boolean(errors.email) || undefined}
            aria-describedby={errors.email ? 'new-user-email-error' : undefined}
            disabled={isSubmitting}
          />
          {errors.email && (
            <p id="new-user-email-error" className="text-xs text-destructive">
              {errors.email}
            </p>
          )}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="new-user-password">Password</Label>
          <Input
            id="new-user-password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            aria-invalid={Boolean(errors.password) || undefined}
            aria-describedby={
              errors.password ? 'new-user-password-error' : undefined
            }
            disabled={isSubmitting}
          />
          {errors.password && (
            <p
              id="new-user-password-error"
              className="text-xs text-destructive"
            >
              {errors.password}
            </p>
          )}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="new-user-role">Role</Label>
          <select
            id="new-user-role"
            value={role}
            onChange={(e) => setRole(e.target.value)}
            disabled={isSubmitting}
            className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          >
            <option value="hr">HR</option>
            <option value="admin">Admin</option>
          </select>
        </div>
      </div>

      {serverError && (
        <div
          role="alert"
          className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive"
        >
          {serverError}
        </div>
      )}

      <div className="flex justify-end">
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Creating...' : 'Create user'}
        </Button>
      </div>
    </form>
  )
}
