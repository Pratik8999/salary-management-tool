import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import App from '../App'
import { clearToken, getToken } from '@/lib/auth'

vi.mock('@/api/auth', () => ({
  login: vi.fn(),
  getMe: vi.fn().mockResolvedValue({
    id: 1,
    email: 'admin@example.com',
    role: 'admin',
    is_active: true,
  }),
}))

import { login } from '@/api/auth'

function renderApp(path = '/login') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  )
}

async function fillAndSubmit(user, email = 'admin@example.com', password = 'secret123') {
  await user.type(screen.getByLabelText(/email/i), email)
  await user.type(screen.getByLabelText(/password/i), password)
  await user.click(screen.getByRole('button', { name: /sign in/i }))
}

describe('LoginPage integration', () => {
  beforeEach(() => {
    clearToken()
    login.mockReset()
  })

  it('stores the token and navigates to the dashboard on success', async () => {
    login.mockResolvedValueOnce({ access_token: 'jwt-abc', token_type: 'bearer' })
    const user = userEvent.setup()
    renderApp()

    await fillAndSubmit(user)

    await waitFor(() => {
      expect(login).toHaveBeenCalledWith({
        email: 'admin@example.com',
        password: 'secret123',
      })
    })
    expect(getToken()).toBe('jwt-abc')
    expect(
      await screen.findByRole('heading', { name: /dashboard/i }),
    ).toBeInTheDocument()
  })

  it('shows the email-does-not-exist error from the server', async () => {
    login.mockRejectedValueOnce({
      response: { status: 401, data: { detail: 'Email does not exist' } },
    })
    const user = userEvent.setup()
    renderApp()

    await fillAndSubmit(user, 'missing@example.com')

    expect(await screen.findByText(/email does not exist/i)).toBeInTheDocument()
    expect(getToken()).toBeNull()
  })

  it('shows the wrong-password error from the server', async () => {
    login.mockRejectedValueOnce({
      response: { status: 401, data: { detail: 'Password is incorrect' } },
    })
    const user = userEvent.setup()
    renderApp()

    await fillAndSubmit(user, 'admin@example.com', 'wrong')

    expect(await screen.findByText(/password is incorrect/i)).toBeInTheDocument()
    expect(getToken()).toBeNull()
  })

  it('shows a fallback message when the request fails without a server response', async () => {
    login.mockRejectedValueOnce(new Error('Network Error'))
    const user = userEvent.setup()
    renderApp()

    await fillAndSubmit(user)

    expect(
      await screen.findByText(/something went wrong/i),
    ).toBeInTheDocument()
  })
})
