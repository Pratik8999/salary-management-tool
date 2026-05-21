import { useEffect, useState } from 'react'
import { useAuth } from '@/lib/AuthContext'
import {
  getOverview,
  getSalaryByCountry,
  getSalaryByJobTitle,
} from '@/api/insights'
import { formatSalary } from '@/lib/currency'

export default function DashboardPage() {
  const { user } = useAuth()

  const [overview, setOverview] = useState(null)
  const [byCountry, setByCountry] = useState(null)
  const [byJobTitle, setByJobTitle] = useState(null)
  const [selectedCountry, setSelectedCountry] = useState('')
  const [loadError, setLoadError] = useState('')

  useEffect(() => {
    let cancelled = false
    async function loadAll() {
      try {
        const [ov, bc] = await Promise.all([getOverview(), getSalaryByCountry()])
        if (cancelled) return
        setOverview(ov)
        setByCountry(bc)
        if (bc.length > 0 && !selectedCountry) {
          setSelectedCountry(bc[0].country)
        }
      } catch (err) {
        if (!cancelled) {
          setLoadError(
            err?.response?.data?.detail || 'Could not load dashboard insights',
          )
        }
      }
    }
    loadAll()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!selectedCountry) return
    let cancelled = false
    setByJobTitle(null)
    getSalaryByJobTitle({ country: selectedCountry })
      .then((data) => {
        if (!cancelled) setByJobTitle(data)
      })
      .catch((err) => {
        if (!cancelled) {
          setLoadError(
            err?.response?.data?.detail ||
              `Could not load salary breakdown for ${selectedCountry}`,
          )
        }
      })
    return () => {
      cancelled = true
    }
  }, [selectedCountry])

  return (
    <div className="space-y-8">
      <header className="space-y-1">
        <h1 className="text-3xl font-semibold tracking-tight">Dashboard</h1>
        {user && (
          <p className="text-sm text-muted-foreground">
            Welcome back, {user.email} · signed in as {user.role}.
          </p>
        )}
      </header>

      {loadError && (
        <div
          role="alert"
          className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive"
        >
          {loadError}
        </div>
      )}

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <KpiTile
          label="Total employees"
          value={overview ? overview.total_headcount.toLocaleString() : '…'}
        />
        <KpiTile
          label="Departments active"
          value={overview ? overview.headcount_by_department.length : '…'}
        />
        <KpiTile
          label="Countries covered"
          value={byCountry ? byCountry.length : '…'}
        />
      </section>

      <p className="text-xs text-muted-foreground">
        Salaries are stored in each employee's local currency, so all amounts
        below are formatted accordingly. There is no single company-wide average
        because that would mix currencies.
      </p>

      <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Panel
          title="Salary by country"
          subtitle="Min, max, and average salary for each country in the directory."
        >
          {byCountry === null ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : byCountry.length === 0 ? (
            <p className="text-sm text-muted-foreground">No data yet.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="py-2 font-medium">Country</th>
                  <th className="py-2 font-medium">Currency</th>
                  <th className="py-2 font-medium text-right">People</th>
                  <th className="py-2 font-medium text-right">Min</th>
                  <th className="py-2 font-medium text-right">Avg</th>
                  <th className="py-2 font-medium text-right">Max</th>
                </tr>
              </thead>
              <tbody>
                {byCountry.map((row) => (
                  <tr key={row.country} className="border-t">
                    <td className="py-2">{row.country}</td>
                    <td className="py-2 text-muted-foreground">
                      {row.currency || '—'}
                    </td>
                    <td className="py-2 text-right tabular-nums">
                      {row.count.toLocaleString()}
                    </td>
                    <td className="py-2 text-right tabular-nums">
                      {formatSalary(row.min)}
                    </td>
                    <td className="py-2 text-right tabular-nums font-medium">
                      {formatSalary(row.avg)}
                    </td>
                    <td className="py-2 text-right tabular-nums">
                      {formatSalary(row.max)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Panel>

        <Panel
          title="Average salary by job title"
          subtitle="Per-role average for the selected country."
          right={
            byCountry && byCountry.length > 0 ? (
              <select
                aria-label="Country"
                className="rounded-md border bg-card px-3 py-1.5 text-sm"
                value={selectedCountry}
                onChange={(e) => setSelectedCountry(e.target.value)}
              >
                {byCountry.map((c) => (
                  <option key={c.country} value={c.country}>
                    {c.country}
                  </option>
                ))}
              </select>
            ) : null
          }
        >
          {byJobTitle === null ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : byJobTitle.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No employees in {selectedCountry}.
            </p>
          ) : (
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="py-2 font-medium">Job title</th>
                  <th className="py-2 font-medium text-right">People</th>
                  <th className="py-2 font-medium text-right">
                    Avg salary
                    {(() => {
                      const selected = byCountry?.find(
                        (c) => c.country === selectedCountry,
                      )
                      return selected?.currency ? ` (${selected.currency})` : ''
                    })()}
                  </th>
                </tr>
              </thead>
              <tbody>
                {byJobTitle.map((row) => (
                  <tr key={row.job_title} className="border-t">
                    <td className="py-2">{row.job_title}</td>
                    <td className="py-2 text-right tabular-nums">
                      {row.count.toLocaleString()}
                    </td>
                    <td className="py-2 text-right tabular-nums font-medium">
                      {formatSalary(row.avg)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Panel>
      </section>

      <Panel
        title="Headcount by department"
        subtitle="Active employees per department."
      >
        {overview === null ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : overview.headcount_by_department.length === 0 ? (
          <p className="text-sm text-muted-foreground">No departments yet.</p>
        ) : (
          <ul className="space-y-2 text-sm">
            {overview.headcount_by_department.map((row) => (
              <li
                key={row.department}
                className="flex items-center justify-between border-b pb-2 last:border-0 last:pb-0"
              >
                <span>{row.department}</span>
                <span className="tabular-nums font-medium">
                  {row.count.toLocaleString()}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  )
}

function KpiTile({ label, value }) {
  return (
    <div className="rounded-xl border bg-card p-5">
      <div className="text-xs uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div className="mt-2 text-3xl font-semibold tabular-nums">{value}</div>
    </div>
  )
}

function Panel({ title, subtitle, right, children }) {
  return (
    <div className="rounded-xl border bg-card p-6">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div className="space-y-0.5">
          <h2 className="text-base font-semibold">{title}</h2>
          {subtitle && (
            <p className="text-xs text-muted-foreground">{subtitle}</p>
          )}
        </div>
        {right}
      </div>
      {children}
    </div>
  )
}
