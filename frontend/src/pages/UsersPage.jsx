import { useEffect, useState } from 'react'
import { listUsers } from '@/api/admin'

function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString()
}

export default function UsersPage() {
  const [users, setUsers] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    setError('')
    setUsers(null)
    listUsers()
      .then((data) => {
        if (active) setUsers(data)
      })
      .catch((err) => {
        if (!active) return
        const detail = err?.response?.data?.detail
        setError(detail || 'Could not load users')
      })
    return () => {
      active = false
    }
  }, [])

  return (
    <main className="min-h-screen bg-muted/40 px-6 py-10">
      <div className="mx-auto max-w-5xl space-y-6">
        <header className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Users</h1>
          <p className="text-sm text-muted-foreground">
            Admin and HR accounts that can sign in.
          </p>
        </header>

        {error && (
          <div
            role="alert"
            className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive"
          >
            {error}
          </div>
        )}

        {!error && users === null && (
          <p className="text-sm text-muted-foreground">Loading users...</p>
        )}

        {!error && users !== null && users.length === 0 && (
          <p className="text-sm text-muted-foreground">No users yet.</p>
        )}

        {!error && users !== null && users.length > 0 && (
          <div className="overflow-hidden rounded-lg border bg-card">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 text-left text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="px-4 py-2 font-medium">Email</th>
                  <th className="px-4 py-2 font-medium">Role</th>
                  <th className="px-4 py-2 font-medium">Status</th>
                  <th className="px-4 py-2 font-medium">Created</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className="border-t">
                    <td className="px-4 py-2">{u.email}</td>
                    <td className="px-4 py-2 capitalize">{u.role}</td>
                    <td className="px-4 py-2">
                      {u.is_active ? 'Active' : 'Inactive'}
                    </td>
                    <td className="px-4 py-2 text-muted-foreground">
                      {formatDate(u.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  )
}
