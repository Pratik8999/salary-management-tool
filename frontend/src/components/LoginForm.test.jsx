import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import LoginForm from './LoginForm'

function setup(props = {}) {
  const onSubmit = vi.fn()
  const user = userEvent.setup()
  render(<LoginForm onSubmit={onSubmit} {...props} />)
  return { user, onSubmit }
}

describe('LoginForm', () => {
  it('renders email, password, and a submit button', () => {
    setup()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /sign in/i }),
    ).toBeInTheDocument()
  })

  it('shows required-field errors when submitting empty', async () => {
    const { user, onSubmit } = setup()
    await user.click(screen.getByRole('button', { name: /sign in/i }))
    expect(screen.getByText(/email is required/i)).toBeInTheDocument()
    expect(screen.getByText(/password is required/i)).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('shows an error for a malformed email', async () => {
    const { user, onSubmit } = setup()
    await user.type(screen.getByLabelText(/email/i), 'not-an-email')
    await user.type(screen.getByLabelText(/password/i), 'secret123')
    await user.click(screen.getByRole('button', { name: /sign in/i }))
    expect(screen.getByText(/enter a valid email/i)).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('calls onSubmit with the credentials when the form is valid', async () => {
    const { user, onSubmit } = setup()
    await user.type(screen.getByLabelText(/email/i), 'admin@example.com')
    await user.type(screen.getByLabelText(/password/i), 'secret123')
    await user.click(screen.getByRole('button', { name: /sign in/i }))
    expect(onSubmit).toHaveBeenCalledWith({
      email: 'admin@example.com',
      password: 'secret123',
    })
  })

  it('disables the submit button while submitting', () => {
    setup({ isSubmitting: true })
    expect(screen.getByRole('button', { name: /signing in/i })).toBeDisabled()
  })

  it('shows a server error message when provided', () => {
    setup({ serverError: 'Email does not exist' })
    expect(screen.getByText(/email does not exist/i)).toBeInTheDocument()
  })
})
