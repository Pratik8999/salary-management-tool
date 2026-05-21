import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { createEmployee, listEmployees } from '@/api/employees'
import EmployeeForm from '@/components/EmployeeForm'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

const PAGE_SIZE = 20

function formatSalary(value, country) {
  if (value == null) return ''
  const num = Number(value)
  if (Number.isNaN(num)) return value
  return num.toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })
}

export default function EmployeesPage() {
  const [query, setQuery] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [page, setPage] = useState(0)
  const [data, setData] = useState(null)
  const [loadError, setLoadError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [createError, setCreateError] = useState('')
  const [isCreating, setIsCreating] = useState(false)

  const fetchPage = useCallback(async () => {
    setIsLoading(true)
    setLoadError('')
    try {
      const result = await listEmployees({
        q: searchTerm || undefined,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      })
      setData(result)
    } catch (err) {
      const detail = err?.response?.data?.detail
      setLoadError(detail || 'Could not load employees')
    } finally {
      setIsLoading(false)
    }
  }, [searchTerm, page])

  useEffect(() => {
    fetchPage()
  }, [fetchPage])

  function handleSearchSubmit(event) {
    event.preventDefault()
    setPage(0)
    setSearchTerm(query.trim())
  }

  async function handleCreate(payload) {
    setIsCreating(true)
    setCreateError('')
    try {
      await createEmployee(payload)
      setShowCreate(false)
      setPage(0)
      await fetchPage()
    } catch (err) {
      const detail = err?.response?.data?.detail
      setCreateError(
        Array.isArray(detail)
          ? detail.map((d) => d.msg).join('; ')
          : detail || 'Could not create employee',
      )
    } finally {
      setIsCreating(false)
    }
  }

  const total = data?.total ?? 0
  const items = data?.items ?? []
  const from = total === 0 ? 0 : page * PAGE_SIZE + 1
  const to = Math.min(total, (page + 1) * PAGE_SIZE)
  const canPrev = page > 0
  const canNext = (page + 1) * PAGE_SIZE < total

  return (
    <div className="space-y-6">
        <header className="flex items-start justify-between gap-4">
          <div className="space-y-1">
            <h1 className="text-2xl font-semibold tracking-tight">Employees</h1>
            <p className="text-sm text-muted-foreground">
              Active employees in the directory.
            </p>
          </div>
          <Button
            type="button"
            onClick={() => {
              setShowCreate((v) => !v)
              setCreateError('')
            }}
          >
            {showCreate ? 'Close' : 'Add employee'}
          </Button>
        </header>

        {showCreate && (
          <section className="space-y-3 rounded-lg border bg-card p-6">
            <div>
              <h2 className="text-base font-medium">Add an employee</h2>
              <p className="text-xs text-muted-foreground">
                New records appear in the list right away.
              </p>
            </div>
            <EmployeeForm
              onSubmit={handleCreate}
              onCancel={() => setShowCreate(false)}
              isSubmitting={isCreating}
              serverError={createError}
              submitLabel="Create employee"
            />
          </section>
        )}

        <form
          onSubmit={handleSearchSubmit}
          className="flex items-center gap-2"
          role="search"
        >
          <Input
            type="search"
            placeholder="Search name, email, or job title"
            aria-label="Search employees"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="max-w-sm"
          />
          <Button type="submit" variant="default" size="sm">
            Search
          </Button>
          {searchTerm && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => {
                setQuery('')
                setSearchTerm('')
                setPage(0)
              }}
            >
              Clear
            </Button>
          )}
        </form>

        {loadError && (
          <div
            role="alert"
            className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive"
          >
            {loadError}
          </div>
        )}

        {!loadError && data === null && (
          <p className="text-sm text-muted-foreground">Loading employees...</p>
        )}

        {!loadError && data !== null && items.length === 0 && (
          <p className="text-sm text-muted-foreground">
            {searchTerm ? 'No employees match that search.' : 'No employees yet.'}
          </p>
        )}

        {!loadError && items.length > 0 && (
          <div className="overflow-hidden rounded-lg border bg-card">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 text-left text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="px-4 py-2 font-medium">Name</th>
                  <th className="px-4 py-2 font-medium">Email</th>
                  <th className="px-4 py-2 font-medium">Job title</th>
                  <th className="px-4 py-2 font-medium">Department</th>
                  <th className="px-4 py-2 font-medium">Country</th>
                  <th className="px-4 py-2 font-medium text-right">Salary</th>
                </tr>
              </thead>
              <tbody>
                {items.map((e) => (
                  <tr key={e.id} className="border-t">
                    <td className="px-4 py-2">
                      <Link
                        to={`/employees/${e.id}`}
                        className="font-medium text-primary hover:underline"
                      >
                        {e.full_name}
                      </Link>
                    </td>
                    <td className="px-4 py-2 text-muted-foreground">{e.email}</td>
                    <td className="px-4 py-2">{e.job_title}</td>
                    <td className="px-4 py-2">{e.department}</td>
                    <td className="px-4 py-2">{e.country}</td>
                    <td className="px-4 py-2 text-right tabular-nums">
                      {formatSalary(e.salary)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {data !== null && total > 0 && (
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>
              Showing {from}–{to} of {total}
            </span>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={!canPrev || isLoading}
              >
                Previous
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => p + 1)}
                disabled={!canNext || isLoading}
              >
                Next
              </Button>
            </div>
          </div>
        )}
    </div>
  )
}
