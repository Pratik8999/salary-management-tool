import { Link } from 'react-router-dom'
import { useAuth } from '@/lib/AuthContext'

export default function DashboardPage() {
  const { user, signOut } = useAuth()
  const isAdmin = user?.role === 'admin'

  return (
    <main className="min-h-screen bg-muted/40 px-6 py-10">
      <div className="mx-auto max-w-5xl space-y-6">
        <header className="flex items-center justify-between">
          <div className="space-y-1">
            <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
            {user && (
              <p className="text-sm text-muted-foreground">
                Signed in as {user.email} ({user.role})
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={signOut}
            className="text-sm text-muted-foreground hover:text-foreground"
          >
            Sign out
          </button>
        </header>

        <nav className="rounded-lg border bg-card p-4 space-x-4">
          <Link
            to="/employees"
            className="text-sm font-medium text-primary hover:underline"
          >
            Employees
          </Link>
          {isAdmin && (
            <Link
              to="/admin/users"
              className="text-sm font-medium text-primary hover:underline"
            >
              Manage users
            </Link>
          )}
          {isAdmin && (
            <Link
              to="/admin/departments"
              className="text-sm font-medium text-primary hover:underline"
            >
              Departments
            </Link>
          )}
        </nav>

        <p className="text-sm text-muted-foreground">
          Placeholder shell — the real dashboard lands in a later slice.
        </p>
      </div>
    </main>
  )
}
