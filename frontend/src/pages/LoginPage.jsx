import LoginForm from '@/components/LoginForm'

export default function LoginPage() {
  function handleSubmit(_credentials) {
    // API integration lands in slice 2
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-muted/40 px-4">
      <div className="w-full max-w-sm space-y-6 rounded-xl border bg-card p-8 shadow-sm">
        <div className="space-y-1 text-center">
          <h1 className="text-2xl font-semibold tracking-tight">Sign in</h1>
          <p className="text-sm text-muted-foreground">
            Salary Management Tool
          </p>
        </div>
        <LoginForm onSubmit={handleSubmit} />
      </div>
    </main>
  )
}
