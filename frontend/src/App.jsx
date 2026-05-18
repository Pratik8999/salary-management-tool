import { Button } from '@/components/ui/button'

function App() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-background text-foreground">
      <div className="text-center px-6 space-y-4">
        <h1 className="text-4xl font-bold">Salary Management Tool</h1>
        <p className="text-muted-foreground">
          Frontend initialized — React + Vite + Tailwind + shadcn/ui.
        </p>
        <div className="flex justify-center gap-3 pt-2">
          <Button>Get Started</Button>
          <Button variant="outline">Learn More</Button>
        </div>
      </div>
    </main>
  )
}

export default App
