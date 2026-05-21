import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import EmployeeForm from './EmployeeForm'

describe('EmployeeForm', () => {
  it('submits a normalized payload (salary as a number)', async () => {
    const onSubmit = vi.fn()
    const user = userEvent.setup()

    render(<EmployeeForm onSubmit={onSubmit} submitLabel="Create employee" />)

    await user.type(screen.getByLabelText(/first name/i), 'Ada')
    await user.type(screen.getByLabelText(/last name/i), 'Lovelace')
    await user.type(screen.getByLabelText(/email/i), 'ada@example.com')
    await user.type(screen.getByLabelText(/job title/i), 'Engineer')
    await user.type(screen.getByLabelText(/department/i), 'Engineering')
    await user.type(screen.getByLabelText(/country/i), 'UK')
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
          department: 'Engineering',
          country: 'UK',
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
    await user.click(screen.getByRole('button', { name: /create employee/i }))

    expect(onSubmit).not.toHaveBeenCalled()
    expect(screen.getAllByText(/required/i).length).toBeGreaterThan(0)
  })
})
