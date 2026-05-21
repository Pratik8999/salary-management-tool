import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getEmployee } from '@/api/employees'
import EmployeeDocumentsPanel from '@/components/EmployeeDocumentsPanel'

function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString()
}

function Field({ label, value }) {
  return (
    <div className="space-y-0.5">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className="text-sm">{value || '—'}</div>
    </div>
  )
}

export default function EmployeeDetailPage() {
  const { id } = useParams()
  const employeeId = Number(id)
  const [employee, setEmployee] = useState(null)
  const [loadError, setLoadError] = useState('')

  useEffect(() => {
    let cancelled = false
    setLoadError('')
    setEmployee(null)
    getEmployee(employeeId)
      .then((data) => {
        if (!cancelled) setEmployee(data)
      })
      .catch((err) => {
        if (cancelled) return
        const detail = err?.response?.data?.detail
        setLoadError(
          err?.response?.status === 404
            ? 'Employee not found'
            : detail || 'Could not load employee',
        )
      })
    return () => {
      cancelled = true
    }
  }, [employeeId])

  return (
    <main className="min-h-screen bg-muted/40 px-6 py-10">
      <div className="mx-auto max-w-5xl space-y-6">
        <div>
          <Link
            to="/employees"
            className="text-sm text-muted-foreground hover:text-foreground"
          >
            ← Back to employees
          </Link>
        </div>

        {loadError && (
          <div
            role="alert"
            className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive"
          >
            {loadError}
          </div>
        )}

        {!loadError && employee === null && (
          <p className="text-sm text-muted-foreground">Loading employee...</p>
        )}

        {employee && (
          <>
            <header className="space-y-1">
              <h1 className="text-2xl font-semibold tracking-tight">
                {employee.full_name}
              </h1>
              <p className="text-sm text-muted-foreground">
                {employee.job_title} · {employee.department} ·{' '}
                {employee.is_active ? 'Active' : 'Inactive'}
              </p>
            </header>

            <section className="grid grid-cols-2 gap-4 rounded-lg border bg-card p-6 md:grid-cols-3">
              <Field label="Email" value={employee.email} />
              <Field label="Country" value={employee.country} />
              <Field
                label="Salary"
                value={Number(employee.salary).toLocaleString()}
              />
              <Field
                label="Employment type"
                value={employee.employment_type?.replace('_', ' ')}
              />
              <Field
                label="Date joined"
                value={formatDate(employee.date_joined)}
              />
              <Field label="Created" value={formatDate(employee.created_at)} />
            </section>

            <EmployeeDocumentsPanel employeeId={employee.id} />
          </>
        )}
      </div>
    </main>
  )
}
