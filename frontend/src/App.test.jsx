import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import App from './App'
import { clearToken, setToken } from '@/lib/auth'

vi.mock('@/api/auth', () => ({
  login: vi.fn(),
  getMe: vi.fn().mockResolvedValue({
    id: 1,
    email: 'admin@example.com',
    role: 'admin',
    is_active: true,
  }),
}))

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  )
}

describe('app routing', () => {
  beforeEach(() => {
    clearToken()
  })

  it('shows the login page at /login', () => {
    renderAt('/login')
    expect(
      screen.getByRole('heading', { name: /sign in/i }),
    ).toBeInTheDocument()
  })

  it('redirects unauthenticated users from /dashboard to /login', () => {
    renderAt('/dashboard')
    expect(
      screen.getByRole('heading', { name: /sign in/i }),
    ).toBeInTheDocument()
  })

  it('renders the dashboard at /dashboard when a token is present', async () => {
    setToken('test-token')
    renderAt('/dashboard')
    expect(
      await screen.findByRole('heading', { name: /dashboard/i }),
    ).toBeInTheDocument()
  })

  it('redirects the root path to the dashboard (and on to login when signed out)', () => {
    renderAt('/')
    expect(
      screen.getByRole('heading', { name: /sign in/i }),
    ).toBeInTheDocument()
  })
})
