import { Link, NavLink, useLocation, useMatch } from 'react-router-dom'
import { useAuth } from '@/lib/AuthContext'

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', icon: IconDashboard },
  { to: '/employees', label: 'Employees', icon: IconUsers },
]

const ADMIN_NAV_ITEMS = [
  { to: '/admin/users', label: 'Users', icon: IconShield },
  { to: '/admin/departments', label: 'Departments', icon: IconBuilding },
]

const CRUMB_LABELS = {
  dashboard: 'Dashboard',
  employees: 'Employees',
  admin: 'Admin',
  users: 'Users',
  departments: 'Departments',
}

export default function AppShell({ children }) {
  const { user, signOut } = useAuth()
  const isAdmin = user?.role === 'admin'

  return (
    <div className="flex min-h-screen bg-muted/30">
      <Sidebar isAdmin={isAdmin} />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar user={user} onSignOut={signOut} />
        <main className="flex-1 overflow-y-auto px-8 py-8">
          <div className="mx-auto max-w-7xl">{children}</div>
        </main>
      </div>
    </div>
  )
}

function Sidebar({ isAdmin }) {
  return (
    <aside className="hidden w-64 shrink-0 border-r border-sidebar-border bg-sidebar text-sidebar-foreground md:flex md:flex-col">
      <div className="flex h-16 items-center gap-2 border-b border-sidebar-border px-6">
        <BrandMark />
        <div className="leading-tight">
          <div className="text-base font-semibold tracking-tight">HRM Tool</div>
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground">
            Salary &amp; People Operations
          </div>
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4 text-sm">
        <NavSection items={NAV_ITEMS} />
        {isAdmin && (
          <>
            <div className="px-3 pb-1 pt-4 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Admin
            </div>
            <NavSection items={ADMIN_NAV_ITEMS} />
          </>
        )}
      </nav>

      <div className="border-t border-sidebar-border px-6 py-4 text-xs text-muted-foreground">
        v1.0 · {new Date().getFullYear()}
      </div>
    </aside>
  )
}

function NavSection({ items }) {
  return (
    <ul className="space-y-0.5">
      {items.map((item) => (
        <li key={item.to}>
          <NavLink
            to={item.to}
            className={({ isActive }) =>
              [
                'flex items-center gap-3 rounded-md px-3 py-2 font-medium transition-colors',
                isActive
                  ? 'bg-sidebar-primary text-sidebar-primary-foreground'
                  : 'text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
              ].join(' ')
            }
          >
            <item.icon className="h-4 w-4" />
            <span>{item.label}</span>
          </NavLink>
        </li>
      ))}
    </ul>
  )
}

function TopBar({ user, onSignOut }) {
  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b bg-card px-8">
      <Breadcrumbs />
      <div className="flex items-center gap-4">
        {user && (
          <div className="flex items-center gap-3">
            <div className="text-right text-sm leading-tight">
              <div className="font-medium">{user.email}</div>
              <div className="text-xs uppercase tracking-wider text-muted-foreground">
                {user.role}
              </div>
            </div>
            <Avatar email={user.email} />
          </div>
        )}
        <button
          type="button"
          onClick={onSignOut}
          className="text-sm font-medium text-muted-foreground hover:text-foreground"
        >
          Sign out
        </button>
      </div>
    </header>
  )
}

function Breadcrumbs() {
  const { pathname } = useLocation()
  const employeeDetailMatch = useMatch('/employees/:id')

  const segments = pathname.split('/').filter(Boolean)
  if (segments.length === 0) return null

  const crumbs = []
  let href = ''
  segments.forEach((seg, i) => {
    href += '/' + seg
    let label = CRUMB_LABELS[seg]
    if (!label && employeeDetailMatch && seg === employeeDetailMatch.params.id) {
      label = `Employee #${seg}`
    }
    if (!label) label = seg
    crumbs.push({ href, label, isLast: i === segments.length - 1 })
  })

  return (
    <nav aria-label="Breadcrumb" className="text-sm">
      <ol className="flex items-center gap-2 text-muted-foreground">
        {crumbs.map((c) => (
          <li key={c.href} className="flex items-center gap-2">
            {c.isLast ? (
              <span className="font-semibold text-foreground">{c.label}</span>
            ) : (
              <Link to={c.href} className="hover:text-foreground">
                {c.label}
              </Link>
            )}
            {!c.isLast && <span className="text-muted-foreground/60">/</span>}
          </li>
        ))}
      </ol>
    </nav>
  )
}

function Avatar({ email }) {
  const initial = (email || '?').trim().charAt(0).toUpperCase()
  return (
    <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
      {initial}
    </div>
  )
}

function BrandMark() {
  return (
    <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary text-primary-foreground">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-5 w-5">
        <path d="M12 1v22M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  )
}

function IconDashboard({ className }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className}>
      <rect x="3" y="3" width="7" height="9" rx="1.5" />
      <rect x="14" y="3" width="7" height="5" rx="1.5" />
      <rect x="14" y="12" width="7" height="9" rx="1.5" />
      <rect x="3" y="16" width="7" height="5" rx="1.5" />
    </svg>
  )
}

function IconUsers({ className }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className}>
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function IconShield({ className }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className}>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function IconBuilding({ className }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className}>
      <rect x="4" y="3" width="16" height="18" rx="1.5" />
      <path d="M9 7h2M13 7h2M9 11h2M13 11h2M9 15h2M13 15h2" strokeLinecap="round" />
    </svg>
  )
}
