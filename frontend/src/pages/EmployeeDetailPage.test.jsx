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
  getEmployee: vi.fn(),
  updateEmployee: vi.fn(),
  listEmployeeDocuments: vi.fn(),
  uploadEmployeeDocument: vi.fn(),
  deleteEmployeeDocument: vi.fn(),
  downloadEmployeeDocument: vi.fn(),
}))
vi.mock('@/api/departments', () => ({
  listDepartments: vi.fn().mockResolvedValue([
    { id: 1, name: 'Engineering', is_active: true },
  ]),
}))

import {
  getEmployee,
  listEmployeeDocuments,
  uploadEmployeeDocument,
} from '@/api/employees'

function renderApp(path = '/employees/42') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  )
}

const EMPLOYEE = {
  id: 42,
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

describe('EmployeeDetailPage', () => {
  beforeEach(() => {
    clearToken()
    getEmployee.mockReset()
    listEmployeeDocuments.mockReset()
    uploadEmployeeDocument.mockReset()
    setToken('jwt-test')
  })

  it('renders employee details with the documents panel', async () => {
    getEmployee.mockResolvedValueOnce(EMPLOYEE)
    listEmployeeDocuments.mockResolvedValueOnce([
      {
        id: 9,
        employee_id: 42,
        uploaded_by_id: 1,
        doc_type: 'offer_letter',
        file_name: 'offer.pdf',
        content_type: 'application/pdf',
        size_bytes: 2048,
        storage_path: 'documents/42/abc.pdf',
        uploaded_at: '2026-05-10T00:00:00Z',
        created_at: '2026-05-10T00:00:00Z',
        updated_at: '2026-05-10T00:00:00Z',
      },
    ])

    renderApp()

    expect(
      await screen.findByRole('heading', { name: 'Ada Lovelace' }),
    ).toBeInTheDocument()
    expect(screen.getByText('ada@example.com')).toBeInTheDocument()
    expect(await screen.findByText('offer.pdf')).toBeInTheDocument()
  })

  it('uploads a document and refreshes the list', async () => {
    getEmployee.mockResolvedValue(EMPLOYEE)
    listEmployeeDocuments
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([
        {
          id: 11,
          employee_id: 42,
          uploaded_by_id: 1,
          doc_type: 'id_proof',
          file_name: 'id.pdf',
          content_type: 'application/pdf',
          size_bytes: 1024,
          storage_path: 'documents/42/xyz.pdf',
          uploaded_at: '2026-05-21T00:00:00Z',
          created_at: '2026-05-21T00:00:00Z',
          updated_at: '2026-05-21T00:00:00Z',
        },
      ])
    uploadEmployeeDocument.mockResolvedValueOnce({})

    const user = userEvent.setup()
    renderApp()

    await screen.findByRole('heading', { name: 'Ada Lovelace' })
    expect(await screen.findByText(/no documents yet/i)).toBeInTheDocument()

    const file = new File([new Uint8Array([1, 2, 3])], 'id.pdf', {
      type: 'application/pdf',
    })
    await user.upload(screen.getByLabelText(/^file$/i), file)
    await user.click(screen.getByRole('button', { name: /^upload$/i }))

    await waitFor(() => {
      expect(uploadEmployeeDocument).toHaveBeenCalledWith(
        42,
        expect.objectContaining({ docType: 'id_proof', file }),
      )
    })
    expect(await screen.findByText('id.pdf')).toBeInTheDocument()
  })
})
