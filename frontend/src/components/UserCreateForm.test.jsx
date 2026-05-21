import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import UserCreateForm from './UserCreateForm'

function setup(props = {}) {
  const onSubmit = vi.fn()
  render(<UserCreateForm onSubmit={onSubmit} {...props} />)
  return { onSubmit, user: userEvent.setup() }
}

describe('UserCreateForm', () => {
  it('renders email, password, role, and a submit button', () => {
    setup()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/role/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /create user/i })).toBeInTheDocument()
  })

  it('shows required-field errors when submitting empty', async () => {
    const { onSubmit, user } = setup()
    await user.click(screen.getByRole('button', { name: /create user/i }))
    expect(screen.getByText(/email is required/i)).toBeInTheDocument()
    expect(screen.getByText(/password is required/i)).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('rejects an invalid email format', async () => {
    const { onSubmit, user } = setup()
    await user.type(screen.getByLabelText(/email/i), 'not-an-email')
    await user.type(screen.getByLabelText(/password/i), 'secret123')
    await user.click(screen.getByRole('button', { name: /create user/i }))
    expect(screen.getByText(/enter a valid email/i)).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('rejects passwords shorter than 8 characters to mirror the backend rule', async () => {
    const { onSubmit, user } = setup()
    await user.type(screen.getByLabelText(/email/i), 'hr@example.com')
    await user.type(screen.getByLabelText(/password/i), 'short')
    await user.click(screen.getByRole('button', { name: /create user/i }))
    expect(
      screen.getByText(/password must be at least 8 characters/i),
    ).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('submits email, password, and the selected role when valid', async () => {
    const { onSubmit, user } = setup()
    await user.type(screen.getByLabelText(/email/i), 'hr@example.com')
    await user.type(screen.getByLabelText(/password/i), 'secret123')
    await user.selectOptions(screen.getByLabelText(/role/i), 'hr')
    await user.click(screen.getByRole('button', { name: /create user/i }))
    expect(onSubmit).toHaveBeenCalledWith({
      email: 'hr@example.com',
      password: 'secret123',
      role: 'hr',
    })
  })

  it('renders the server error when provided', () => {
    setup({ serverError: 'Email already exists' })
    expect(screen.getByRole('alert')).toHaveTextContent(/email already exists/i)
  })

  it('disables the submit button while submitting', () => {
    setup({ isSubmitting: true })
    expect(screen.getByRole('button', { name: /creating/i })).toBeDisabled()
  })
})
