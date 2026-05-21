import { useAuth } from '@/lib/AuthContext'

export default function DashboardPage() {
  const { user } = useAuth()

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-3xl font-semibold tracking-tight">Dashboard</h1>
        {user && (
          <p className="text-sm text-muted-foreground">
            Welcome back, {user.email} · signed in as {user.role}.
          </p>
        )}
      </header>

      <section className="rounded-xl border bg-card p-8 text-sm text-muted-foreground">
        Placeholder shell — KPI tiles and salary charts land in the next slice.
      </section>
    </div>
  )
}
