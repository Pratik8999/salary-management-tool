import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import App from '../App'
import { setToken, clearToken } from '@/lib/auth'

vi.mock('@/api/auth', () => ({
  login: vi.fn(),
  getMe: vi.fn(),
}))
vi.mock('@/api/admin', () => ({
  listUsers: vi.fn().mockResolvedValue([]),
  createUser: vi.fn(),
}))

import { getMe } from '@/api/auth'
import { listUsers } from '@/api/admin'

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  )
}

describe('admin-only routes', () => {
  beforeEach(() => {
    clearToken()
    getMe.mockReset()
    listUsers.mockClear()
  })

  it('lets an admin reach /admin/users', async () => {
    setToken('jwt-admin')
    getMe.mockResolvedValue({
      id: 1,
      email: 'admin@example.com',
      role: 'admin',
      is_active: true,
    })

    renderAt('/admin/users')

    expect(
      await screen.findByRole('heading', { name: /users/i }),
    ).toBeInTheDocument()
    expect(listUsers).toHaveBeenCalled()
  })

  it('redirects an HR user away from /admin/users to /dashboard', async () => {
    setToken('jwt-hr')
    getMe.mockResolvedValue({
      id: 2,
      email: 'hr@example.com',
      role: 'hr',
      is_active: true,
    })

    renderAt('/admin/users')

    expect(
      await screen.findByRole('heading', { name: /dashboard/i }),
    ).toBeInTheDocument()
    await waitFor(() => {
      expect(listUsers).not.toHaveBeenCalled()
    })
  })

  it('shows the "Manage users" link on the dashboard for admins', async () => {
    setToken('jwt-admin')
    getMe.mockResolvedValue({
      id: 1,
      email: 'admin@example.com',
      role: 'admin',
      is_active: true,
    })

    renderAt('/dashboard')

    expect(
      await screen.findByRole('link', { name: /manage users/i }),
    ).toBeInTheDocument()
  })

  it('hides the "Manage users" link on the dashboard for HR users', async () => {
    setToken('jwt-hr')
    getMe.mockResolvedValue({
      id: 2,
      email: 'hr@example.com',
      role: 'hr',
      is_active: true,
    })

    renderAt('/dashboard')

    expect(
      await screen.findByRole('heading', { name: /dashboard/i }),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('link', { name: /manage users/i }),
    ).not.toBeInTheDocument()
  })

  it('redirects to /login when /auth/me fails (e.g. stale token)', async () => {
    setToken('stale-token')
    getMe.mockRejectedValue({ response: { status: 401 } })

    renderAt('/admin/users')

    expect(
      await screen.findByRole('heading', { name: /sign in/i }),
    ).toBeInTheDocument()
  })
})
