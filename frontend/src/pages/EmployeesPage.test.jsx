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
    email: 'hr@example.com',
    role: 'hr',
    is_active: true,
  }),
}))
vi.mock('@/api/employees', () => ({
  listEmployees: vi.fn(),
  listDepartments: vi.fn(),
}))

import { listEmployees } from '@/api/employees'

function renderApp(path = '/employees') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  )
}

const ADA = {
  id: 1,
  first_name: 'Ada',
  last_name: 'Lovelace',
  full_name: 'Ada Lovelace',
  email: 'ada@example.com',
  job_title: 'Software Engineer',
  department: 'Engineering',
  country: 'UK',
  salary: '50000.00',
  employment_type: 'full_time',
  date_joined: '2024-01-15',
  is_active: true,
  created_by_id: 1,
  created_at: '2026-05-01T00:00:00Z',
  updated_at: '2026-05-01T00:00:00Z',
}

describe('EmployeesPage', () => {
  beforeEach(() => {
    clearToken()
    listEmployees.mockReset()
    setToken('jwt-test')
  })

  it('renders the employee list and filters via search', async () => {
    listEmployees
      .mockResolvedValueOnce({ items: [ADA], total: 1, limit: 20, offset: 0 })
      .mockResolvedValueOnce({
        items: [{ ...ADA, id: 2, full_name: 'Grace Hopper', email: 'grace@example.com' }],
        total: 1,
        limit: 20,
        offset: 0,
      })

    const user = userEvent.setup()
    renderApp()

    expect(await screen.findByText('Ada Lovelace')).toBeInTheDocument()
    expect(screen.getByText('Showing 1–1 of 1')).toBeInTheDocument()

    await user.type(screen.getByLabelText(/search employees/i), 'grace')
    await user.click(screen.getByRole('button', { name: /^search$/i }))

    await waitFor(() => {
      expect(listEmployees).toHaveBeenLastCalledWith(
        expect.objectContaining({ q: 'grace', offset: 0 }),
      )
    })
    expect(await screen.findByText('Grace Hopper')).toBeInTheDocument()
  })
})
