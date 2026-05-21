import { useCallback, useEffect, useState } from 'react'
import {
  createDepartment,
  listDepartments,
  updateDepartment,
} from '@/api/departments'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

function readDetail(err, fallback) {
  const detail = err?.response?.data?.detail
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join('; ')
  return detail || fallback
}

export default function DepartmentsPage() {
  const [departments, setDepartments] = useState(null)
  const [loadError, setLoadError] = useState('')
  const [newName, setNewName] = useState('')
  const [createError, setCreateError] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [editName, setEditName] = useState('')
  const [editError, setEditError] = useState('')
  const [busyId, setBusyId] = useState(null)

  const refresh = useCallback(async () => {
    setLoadError('')
    try {
      const data = await listDepartments({ includeInactive: true })
      setDepartments(data)
    } catch (err) {
      setLoadError(readDetail(err, 'Could not load departments'))
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  async function handleCreate(event) {
    event.preventDefault()
    if (!newName.trim()) {
      setCreateError('Name is required')
      return
    }
    setIsCreating(true)
    setCreateError('')
    try {
      await createDepartment({ name: newName.trim() })
      setNewName('')
      await refresh()
    } catch (err) {
      setCreateError(readDetail(err, 'Could not create department'))
    } finally {
      setIsCreating(false)
    }
  }

  function startEdit(dept) {
    setEditingId(dept.id)
    setEditName(dept.name)
    setEditError('')
  }

  async function saveEdit(dept) {
    if (!editName.trim()) {
      setEditError('Name is required')
      return
    }
    setBusyId(dept.id)
    setEditError('')
    try {
      await updateDepartment(dept.id, { name: editName.trim() })
      setEditingId(null)
      await refresh()
    } catch (err) {
      setEditError(readDetail(err, 'Could not update department'))
    } finally {
      setBusyId(null)
    }
  }

  async function toggleActive(dept) {
    setBusyId(dept.id)
    setEditError('')
    try {
      await updateDepartment(dept.id, { is_active: !dept.is_active })
      await refresh()
    } catch (err) {
      setEditError(readDetail(err, 'Could not update department'))
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
        <header className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Departments</h1>
          <p className="text-sm text-muted-foreground">
            The list HR picks from when adding employees.
          </p>
        </header>

        <section className="space-y-3 rounded-lg border bg-card p-6">
          <div>
            <h2 className="text-base font-medium">Add a department</h2>
          </div>
          <form
            onSubmit={handleCreate}
            className="flex flex-wrap items-end gap-3"
          >
            <div className="space-y-1.5">
              <Label htmlFor="new-dept-name">Name</Label>
              <Input
                id="new-dept-name"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                disabled={isCreating}
                className="w-72"
              />
            </div>
            <Button type="submit" disabled={isCreating}>
              {isCreating ? 'Adding...' : 'Add department'}
            </Button>
          </form>
          {createError && (
            <p role="alert" className="text-xs text-destructive">
              {createError}
            </p>
          )}
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

        {!loadError && departments === null && (
          <p className="text-sm text-muted-foreground">Loading departments...</p>
        )}

        {!loadError && departments && departments.length === 0 && (
          <p className="text-sm text-muted-foreground">No departments yet.</p>
        )}

        {!loadError && departments && departments.length > 0 && (
          <div className="overflow-hidden rounded-lg border bg-card">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 text-left text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="px-4 py-2 font-medium">Name</th>
                  <th className="px-4 py-2 font-medium">Status</th>
                  <th className="px-4 py-2 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {departments.map((d) => {
                  const rowBusy = busyId === d.id
                  const isEditing = editingId === d.id
                  return (
                    <tr key={d.id} className="border-t">
                      <td className="px-4 py-2">
                        {isEditing ? (
                          <Input
                            value={editName}
                            onChange={(e) => setEditName(e.target.value)}
                            disabled={rowBusy}
                            aria-label={`New name for ${d.name}`}
                          />
                        ) : (
                          d.name
                        )}
                      </td>
                      <td className="px-4 py-2">
                        {d.is_active ? 'Active' : 'Inactive'}
                      </td>
                      <td className="px-4 py-2 text-right space-x-2">
                        {isEditing ? (
                          <>
                            <Button
                              type="button"
                              variant="default"
                              size="sm"
                              disabled={rowBusy}
                              onClick={() => saveEdit(d)}
                            >
                              Save
                            </Button>
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              disabled={rowBusy}
                              onClick={() => setEditingId(null)}
                            >
                              Cancel
                            </Button>
                          </>
                        ) : (
                          <>
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              disabled={rowBusy}
                              onClick={() => startEdit(d)}
                            >
                              Rename
                            </Button>
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              disabled={rowBusy}
                              onClick={() => toggleActive(d)}
                            >
                              {d.is_active ? 'Deactivate' : 'Activate'}
                            </Button>
                          </>
                        )}
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
