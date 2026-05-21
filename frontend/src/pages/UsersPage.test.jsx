import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import App from '../App'
import { setToken, clearToken } from '@/lib/auth'

vi.mock('@/api/auth', () => ({
  login: vi.fn(),
  getMe: vi.fn().mockResolvedValue({
    id: 1,
    email: 'admin@example.com',
    role: 'admin',
    is_active: true,
  }),
}))
vi.mock('@/api/admin', () => ({
  listUsers: vi.fn(),
  createUser: vi.fn(),
  updateUser: vi.fn(),
}))

import { listUsers, createUser, updateUser } from '@/api/admin'

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
    createUser.mockReset()
    updateUser.mockReset()
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

    expect(await screen.findByText(/loading users/i)).toBeInTheDocument()
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

  it('creates a user and refreshes the list', async () => {
    listUsers
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([
        {
          id: 7,
          email: 'new-hr@example.com',
          role: 'hr',
          is_active: true,
          created_at: '2026-05-21T00:00:00Z',
          updated_at: '2026-05-21T00:00:00Z',
        },
      ])
    createUser.mockResolvedValueOnce({
      id: 7,
      email: 'new-hr@example.com',
      role: 'hr',
      is_active: true,
      created_at: '2026-05-21T00:00:00Z',
      updated_at: '2026-05-21T00:00:00Z',
    })

    const user = userEvent.setup()
    renderApp()

    expect(await screen.findByText(/no users yet/i)).toBeInTheDocument()
    await user.type(screen.getByLabelText(/email/i), 'new-hr@example.com')
    await user.type(screen.getByLabelText(/password/i), 'secret123')
    await user.selectOptions(screen.getByLabelText(/role/i), 'hr')
    await user.click(screen.getByRole('button', { name: /create user/i }))

    await waitFor(() => {
      expect(createUser).toHaveBeenCalledWith({
        email: 'new-hr@example.com',
        password: 'secret123',
        role: 'hr',
      })
    })
    expect(await screen.findByText('new-hr@example.com')).toBeInTheDocument()
    expect(listUsers).toHaveBeenCalledTimes(2)
  })

  it('deactivates a user via a row action and refreshes the list', async () => {
    const activeRow = {
      id: 7,
      email: 'hr@example.com',
      role: 'hr',
      is_active: true,
      created_at: '2026-05-21T00:00:00Z',
      updated_at: '2026-05-21T00:00:00Z',
    }
    const deactivatedRow = { ...activeRow, is_active: false }
    listUsers
      .mockResolvedValueOnce([activeRow])
      .mockResolvedValueOnce([deactivatedRow])
    updateUser.mockResolvedValueOnce(deactivatedRow)

    const user = userEvent.setup()
    renderApp()

    await screen.findByText('hr@example.com')
    await user.click(
      screen.getByRole('button', { name: /deactivate hr@example\.com/i }),
    )

    await waitFor(() => {
      expect(updateUser).toHaveBeenCalledWith(7, { is_active: false })
    })
    expect(await screen.findByText(/inactive/i)).toBeInTheDocument()
    expect(listUsers).toHaveBeenCalledTimes(2)
  })

  it('reactivates an inactive user', async () => {
    const inactiveRow = {
      id: 8,
      email: 'old-hr@example.com',
      role: 'hr',
      is_active: false,
      created_at: '2026-05-01T00:00:00Z',
      updated_at: '2026-05-01T00:00:00Z',
    }
    const activeRow = { ...inactiveRow, is_active: true }
    listUsers
      .mockResolvedValueOnce([inactiveRow])
      .mockResolvedValueOnce([activeRow])
    updateUser.mockResolvedValueOnce(activeRow)

    const user = userEvent.setup()
    renderApp()

    await screen.findByText('old-hr@example.com')
    await user.click(
      screen.getByRole('button', { name: /activate old-hr@example\.com/i }),
    )

    await waitFor(() => {
      expect(updateUser).toHaveBeenCalledWith(8, { is_active: true })
    })
  })

  it('changes a user role via the per-row role selector', async () => {
    const hrRow = {
      id: 9,
      email: 'someone@example.com',
      role: 'hr',
      is_active: true,
      created_at: '2026-05-01T00:00:00Z',
      updated_at: '2026-05-01T00:00:00Z',
    }
    listUsers
      .mockResolvedValueOnce([hrRow])
      .mockResolvedValueOnce([{ ...hrRow, role: 'admin' }])
    updateUser.mockResolvedValueOnce({ ...hrRow, role: 'admin' })

    const user = userEvent.setup()
    renderApp()

    await screen.findByText('someone@example.com')
    await user.selectOptions(
      screen.getByRole('combobox', { name: /role for someone@example\.com/i }),
      'admin',
    )

    await waitFor(() => {
      expect(updateUser).toHaveBeenCalledWith(9, { role: 'admin' })
    })
  })

  it('shows a server error when an edit fails', async () => {
    const row = {
      id: 42,
      email: 'someone-else@example.com',
      role: 'hr',
      is_active: true,
      created_at: '2026-05-01T00:00:00Z',
      updated_at: '2026-05-01T00:00:00Z',
    }
    listUsers.mockResolvedValue([row])
    updateUser.mockRejectedValueOnce({
      response: { status: 400, data: { detail: 'Could not update user' } },
    })

    const user = userEvent.setup()
    renderApp()

    await screen.findByText('someone-else@example.com')
    await user.click(
      screen.getByRole('button', {
        name: /deactivate someone-else@example\.com/i,
      }),
    )

    expect(
      await screen.findByText(/could not update user/i),
    ).toBeInTheDocument()
  })

  it('disables the deactivate button for the currently signed-in admin', async () => {
    listUsers.mockResolvedValueOnce([
      {
        id: 1,
        email: 'admin@example.com',
        role: 'admin',
        is_active: true,
        created_at: '2026-05-01T00:00:00Z',
        updated_at: '2026-05-01T00:00:00Z',
      },
    ])
    renderApp()
    await screen.findByText('admin@example.com')
    expect(
      screen.getByRole('button', { name: /deactivate admin@example\.com/i }),
    ).toBeDisabled()
    expect(
      screen.getByRole('combobox', { name: /role for admin@example\.com/i }),
    ).toBeDisabled()
  })

  it('surfaces the server error when create fails', async () => {
    listUsers.mockResolvedValueOnce([])
    createUser.mockRejectedValueOnce({
      response: { status: 409, data: { detail: 'Email already exists' } },
    })

    const user = userEvent.setup()
    renderApp()

    await screen.findByText(/no users yet/i)
    await user.type(screen.getByLabelText(/email/i), 'dup@example.com')
    await user.type(screen.getByLabelText(/password/i), 'secret123')
    await user.click(screen.getByRole('button', { name: /create user/i }))

    expect(await screen.findByText(/email already exists/i)).toBeInTheDocument()
  })
})
