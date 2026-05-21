import { useCallback, useEffect, useState } from 'react'
import { createUser, listUsers, updateUser } from '@/api/admin'
import { Button } from '@/components/ui/button'
import SuccessBanner from '@/components/SuccessBanner'
import UserCreateForm from '@/components/UserCreateForm'
import { useAuth } from '@/lib/AuthContext'

function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString()
}

export default function UsersPage() {
  const { user: currentUser } = useAuth()
  const [users, setUsers] = useState(null)
  const [loadError, setLoadError] = useState('')
  const [createError, setCreateError] = useState('')
  const [editError, setEditError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [busyUserId, setBusyUserId] = useState(null)

  const fetchUsers = useCallback(async () => {
    setLoadError('')
    try {
      const data = await listUsers()
      setUsers(data)
    } catch (err) {
      const detail = err?.response?.data?.detail
      setLoadError(detail || 'Could not load users')
    }
  }, [])

  useEffect(() => {
    fetchUsers()
  }, [fetchUsers])

  async function handleCreate(payload) {
    setIsSubmitting(true)
    setCreateError('')
    try {
      await createUser(payload)
      await fetchUsers()
      setSuccessMessage(`User ${payload.email} created.`)
    } catch (err) {
      const detail = err?.response?.data?.detail
      setCreateError(detail || 'Could not create user')
    } finally {
      setIsSubmitting(false)
    }
  }

  async function applyUpdate(userId, payload) {
    setBusyUserId(userId)
    setEditError('')
    try {
      await updateUser(userId, payload)
      await fetchUsers()
      setSuccessMessage('User updated.')
    } catch (err) {
      const detail = err?.response?.data?.detail
      setEditError(detail || 'Could not update user')
    } finally {
      setBusyUserId(null)
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
        <header className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Users</h1>
          <p className="text-sm text-muted-foreground">
            Admin and HR accounts that can sign in.
          </p>
        </header>

        <SuccessBanner
          message={successMessage}
          onDismiss={() => setSuccessMessage('')}
        />

        <section className="space-y-3 rounded-lg border bg-card p-6">
          <div>
            <h2 className="text-base font-medium">Add a user</h2>
            <p className="text-xs text-muted-foreground">
              New accounts can sign in immediately.
            </p>
          </div>
          <UserCreateForm
            onSubmit={handleCreate}
            isSubmitting={isSubmitting}
            serverError={createError}
          />
        </section>

        {editError && (
          <div
            role="alert"
            className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive"
          >
            {editError}
          </div>
        )}

        {loadError && (
          <div
            role="alert"
            className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive"
          >
            {loadError}
          </div>
        )}

        {!loadError && users === null && (
          <p className="text-sm text-muted-foreground">Loading users...</p>
        )}

        {!loadError && users !== null && users.length === 0 && (
          <p className="text-sm text-muted-foreground">No users yet.</p>
        )}

        {!loadError && users !== null && users.length > 0 && (
          <div className="overflow-hidden rounded-lg border bg-card">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 text-left text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="px-4 py-2 font-medium">Email</th>
                  <th className="px-4 py-2 font-medium">Role</th>
                  <th className="px-4 py-2 font-medium">Status</th>
                  <th className="px-4 py-2 font-medium">Created</th>
                  <th className="px-4 py-2 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => {
                  const isSelf = currentUser?.id === u.id
                  const rowBusy = busyUserId === u.id
                  return (
                    <tr key={u.id} className="border-t">
                      <td className="px-4 py-2">{u.email}</td>
                      <td className="px-4 py-2">
                        <select
                          aria-label={`Role for ${u.email}`}
                          value={u.role}
                          disabled={isSelf || rowBusy}
                          onChange={(e) =>
                            applyUpdate(u.id, { role: e.target.value })
                          }
                          className="h-8 rounded-md border border-input bg-transparent px-2 text-sm capitalize disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          <option value="hr">HR</option>
                          <option value="admin">Admin</option>
                        </select>
                      </td>
                      <td className="px-4 py-2">
                        {u.is_active ? 'Active' : 'Inactive'}
                      </td>
                      <td className="px-4 py-2 text-muted-foreground">
                        {formatDate(u.created_at)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          disabled={(isSelf && u.is_active) || rowBusy}
                          aria-label={
                            u.is_active
                              ? `Deactivate ${u.email}`
                              : `Activate ${u.email}`
                          }
                          onClick={() =>
                            applyUpdate(u.id, { is_active: !u.is_active })
                          }
                        >
                          {u.is_active ? 'Deactivate' : 'Activate'}
                        </Button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
    </div>
  )
}
