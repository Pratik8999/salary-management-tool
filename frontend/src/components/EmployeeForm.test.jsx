import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import EmployeeForm from './EmployeeForm'

vi.mock('@/api/departments', () => ({
  listDepartments: vi.fn(),
}))
vi.mock('@/api/countries', () => ({
  listAllCountries: vi.fn(),
}))

import { listDepartments } from '@/api/departments'
import { listAllCountries } from '@/api/countries'

const DEPTS = [
  { id: 1, name: 'Engineering', is_active: true },
  { id: 2, name: 'Sales', is_active: true },
]

const COUNTRIES = [
  { name: 'India', currency: 'INR' },
  { name: 'United Kingdom', currency: 'GBP' },
  { name: 'United States', currency: 'USD' },
]

describe('EmployeeForm', () => {
  beforeEach(() => {
    listDepartments.mockReset()
    listDepartments.mockResolvedValue(DEPTS)
    listAllCountries.mockReset()
    listAllCountries.mockResolvedValue(COUNTRIES)
  })

  it('submits a normalized payload (department_id + salary as numbers)', async () => {
    const onSubmit = vi.fn()
    const user = userEvent.setup()

    render(<EmployeeForm onSubmit={onSubmit} submitLabel="Create employee" />)

    await screen.findByRole('option', { name: 'Engineering' })

    await user.type(screen.getByLabelText(/first name/i), 'Ada')
    await user.type(screen.getByLabelText(/last name/i), 'Lovelace')
    await user.type(screen.getByLabelText(/email/i), 'ada@example.com')
    await user.type(screen.getByLabelText(/job title/i), 'Engineer')
    await user.selectOptions(screen.getByLabelText(/department/i), '1')
    await screen.findByRole('option', { name: 'United Kingdom' })
    await user.selectOptions(screen.getByLabelText(/country/i), 'United Kingdom')
    await user.type(screen.getByLabelText(/salary/i), '50000')
    await user.type(screen.getByLabelText(/date joined/i), '2024-01-15')

    await user.click(screen.getByRole('button', { name: /create employee/i }))

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          first_name: 'Ada',
          last_name: 'Lovelace',
          email: 'ada@example.com',
          job_title: 'Engineer',
          department_id: 1,
          country: 'United Kingdom',
          salary: 50000,
          date_joined: '2024-01-15',
          employment_type: 'full_time',
        }),
      )
    })
  })

  it('blocks submission when required fields are missing', async () => {
    const onSubmit = vi.fn()
    const user = userEvent.setup()

    render(<EmployeeForm onSubmit={onSubmit} submitLabel="Create employee" />)
    await screen.findByRole('option', { name: 'Engineering' })
    await user.click(screen.getByRole('button', { name: /create employee/i }))

    expect(onSubmit).not.toHaveBeenCalled()
    expect(screen.getAllByText(/required/i).length).toBeGreaterThan(0)
  })
})
