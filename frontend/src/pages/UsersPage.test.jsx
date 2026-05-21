import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import App from '../App'
import { setToken, clearToken } from '@/lib/auth'

vi.mock('@/api/admin', () => ({
  listUsers: vi.fn(),
}))

import { listUsers } from '@/api/admin'

function renderApp(path = '/admin/users') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  )
}

describe('UsersPage', () => {
  beforeEach(() => {
    clearToken()
    listUsers.mockReset()
    setToken('jwt-test')
  })

  it('redirects to /login when no token is set', async () => {
    clearToken()
    renderApp()
    expect(
      await screen.findByRole('heading', { name: /sign in/i }),
    ).toBeInTheDocument()
    expect(listUsers).not.toHaveBeenCalled()
  })

  it('renders rows from the admin/users endpoint', async () => {
    listUsers.mockResolvedValueOnce([
      {
        id: 1,
        email: 'admin@example.com',
        role: 'admin',
        is_active: true,
        created_at: '2026-05-01T00:00:00Z',
        updated_at: '2026-05-01T00:00:00Z',
      },
      {
        id: 2,
        email: 'hr@example.com',
        role: 'hr',
        is_active: false,
        created_at: '2026-05-02T00:00:00Z',
        updated_at: '2026-05-02T00:00:00Z',
      },
    ])

    renderApp()

    expect(await screen.findByText('admin@example.com')).toBeInTheDocument()
    expect(screen.getByText('hr@example.com')).toBeInTheDocument()
    expect(screen.getAllByRole('row')).toHaveLength(3)
  })

  it('shows a loading indicator while the request is in flight', async () => {
    let resolveFn
    listUsers.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveFn = resolve
      }),
    )

    renderApp()

    expect(screen.getByText(/loading users/i)).toBeInTheDocument()
    resolveFn([])
    await waitFor(() => {
      expect(screen.queryByText(/loading users/i)).not.toBeInTheDocument()
    })
  })

  it('shows an empty state when no users are returned', async () => {
    listUsers.mockResolvedValueOnce([])
    renderApp()
    expect(await screen.findByText(/no users yet/i)).toBeInTheDocument()
  })

  it('shows an error when the request fails', async () => {
    listUsers.mockRejectedValueOnce({
      response: { status: 403, data: { detail: 'Admins only' } },
    })
    renderApp()
    expect(await screen.findByText(/admins only/i)).toBeInTheDocument()
  })

  it('shows a fallback error when the request fails without a server response', async () => {
    listUsers.mockRejectedValueOnce(new Error('Network Error'))
    renderApp()
    expect(
      await screen.findByText(/could not load users/i),
    ).toBeInTheDocument()
  })
})
