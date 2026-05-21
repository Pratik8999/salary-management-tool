# Development Plan — Salary Management Tool

This document captures the plan I followed while building the Salary Management Tool. It lays out the phases of work, the order in which they were tackled, and the reasoning behind that order.

---

## Conventions

**TDD.** For anything with behaviour — validators, hashing, role checks, API handlers — a failing test is written first, then the implementation that turns it green. Pure data declarations (SQLAlchemy column definitions with no logic) are not tested directly; they are exercised through the endpoint and model-logic tests that sit above them.

**Vertical slices.** Each user-visible capability is built end-to-end (model → schema → endpoint → test) before moving on, rather than building every model first and then every API.

**Ordering by dependency.** Foundational, auth-bearing entities come before domain entities that depend on them. User precedes Employee, Employee precedes Salary and Leave.

---

## Phase 0 — Repository foundation

Goal: a monorepo where backend and frontend can evolve independently but share a single git history.

- Monorepo scaffold with `backend/` (FastAPI) and `frontend/` (Vite + React + Tailwind), top-level README and `.gitignore`.
- shadcn/ui added to the frontend so component primitives are in place before any UI work begins.

---

## Phase 1 — Containerization & local dev loop

Goal: a single `docker compose up` brings the whole stack online. Doing this before feature work means every feature afterwards is developed and tested against the real runtime, not a mocked one.

1. Backend Dockerfile and `.dockerignore`.
2. Frontend Dockerfile and `.dockerignore`.
3. Root `docker-compose.yml` with backend, frontend, and PostgreSQL; a `.env.example` documents the variables.
4. README rewritten to lead with run instructions.

**Exit criteria.** Cloning the repo and running `docker compose up` from a clean machine yields a reachable backend on `:8000`, a reachable frontend on `:5173`, and a healthy database.

---

## Phase 2 — Database & migration plumbing

Goal: wire the persistence layer once, so every model from Phase 3 onwards is a clean migration commit rather than a model-plus-infra commit.

1. SQLAlchemy engine, session factory, and declarative `Base`. A `/health/db` endpoint that opens a session, so connectivity is visible.
2. Alembic initialised with an empty baseline revision.
3. Test infrastructure: pytest with an `httpx.AsyncClient` fixture and a transactional test-database fixture that rolls back after each test. One smoke test against `/health`.

**Exit criteria.** `pytest` is green, `alembic upgrade head` is idempotent, and the test database is fully isolated from the dev database.

---

## Phase 3 — User domain

User is built first because every protected endpoint downstream depends on an authenticated HR or Admin user. Three iterations.

### 3A · User model and password hashing
- Tests assert that setting a password stores a hash (never the plaintext), that `verify_password` round-trips correctly, and that the `role` field accepts only `admin` and `hr`.
- The model and its Alembic migration follow.

### 3B · Authentication
- Tests for `POST /auth/login` cover the happy path, wrong-password, unknown-user, and inactive-user cases.
- JWT issue/verify utilities, the login endpoint, and a `get_current_user` dependency follow.
- Role-guard dependencies (`get_current_admin`, `get_current_hr`) are built and tested in isolation so the guards themselves are exercised, not just the endpoints that use them.

### 3C · Admin manages HR users
Each endpoint is built as its own slice — test first, then implementation — so the CRUD shape grows one capability at a time.

- `POST /admin/users` — admin creates an HR user.
- `GET /admin/users` — admin lists users.
- `PATCH /admin/users/{id}` — admin edits a user (deactivate, change role, etc.).

**Exit criteria.** An admin can log in, create an HR user, list users, and edit a user end-to-end. All paths are covered by tests.

---

## Phase 4 — Employee domain

With authenticated HR users in place, the Employee entity becomes meaningful.

### 4A · Employee model
Tests cover the model-level invariants — computed full name, unique email, employment-type enum, validators on salary and joining-date. Pure columns are not tested directly. Model and migration follow.

### 4B · First slice of Employee CRUD
One endpoint per slice, test-first.

- `POST /employees`
- `GET /employees` — paginated and searchable. The brief mentions ~10,000 employees, so the list endpoint is designed with that scale in mind from the start (server-side pagination, indexed search columns). `GET /employees/departments` ships alongside as the dropdown source.

### 4C · Normalise `department` into its own table
The list endpoint exposes a tension: department was a free-form string on Employee, drift-prone and awkward for a system judged on design thinking. Before more features pile on top of the string, `department` is lifted into its own table. A data-safe Alembic migration folds the existing distinct values into the new table, backfills a FK on `employees`, and drops the old column. Auto-create-on-write keeps the API contract unchanged for callers — they still pass a department name.

### 4D · Finish Employee CRUD
With the FK in place, the remaining endpoints land:

- `GET /employees/{id}`
- `PATCH /employees/{id}` — partial updates; department changes go through the same auto-create path as POST.
- `DELETE /employees/{id}` — soft-delete (sets `is_active=false`). The audit trail is preserved, salary-insight aggregates downstream can still see history if needed, and the `is_active` column already existed.
- `GET /employees?country=...` — country filter on the list endpoint, anticipating the salary-insights drilldown in Phase 5.

**Exit criteria.** HR (or admin) can run a full CRUD lifecycle on employees via the API. Pagination, search, country and department filters, and soft-delete are all covered by tests.

---

## Phase 5 — Salary insights

The brief explicitly asks for cross-cutting salary reports. These are read-only aggregates over the Employee table — no new tables are introduced.

- `GET /insights/salary/by-country` — min, max, avg, and headcount per country.
- `GET /insights/salary/by-job-title?country=...` — average salary per job title within a given country (the brief phrases it as "for the given job title in a country", so country is the anchor and required).
- `GET /insights/salary/by-department` — an extra meaningful metric for the HR persona: headcount and average salary per department. Joins through the normalised `departments` table introduced in Phase 4C.

All three exclude inactive employees by default, are HR/admin-only, and order their results deterministically so the UI can render without extra sorting.

---

## Phase 6 — Employee documents

A real HR operation that the brief leaves room for under "any other meaningful data": ID proof, offer letter, contract, and the general "other" category. Files land on a host-bound mount so they're visible on the developer's filesystem outside Docker too, not hidden inside a named volume.

- `EmployeeDocument` model — FK to Employee with `ON DELETE CASCADE` (orphan documents are useless), FK to User on `uploaded_by` with `RESTRICT` so the audit trail is intact even as HR users churn. Doc-type is a four-value enum.
- `POST /employees/{id}/documents` — multipart upload. Whitelisted content types only (PDF, PNG, JPEG), 5 MB cap. Filename is preserved for display; the on-disk path uses a UUID to avoid collisions.
- `GET /employees/{id}/documents` — list metadata.
- `GET /employees/{id}/documents/{doc_id}/download` — streams the file.
- `DELETE /employees/{id}/documents/{doc_id}` — removes the row and the file together.

---

## Phase 7 — Frontend slices

Frontend work begins once the backend API contract is stable. Each screen is built as its own slice, with a component test where the screen has non-trivial logic.

1. Login screen — calls `/auth/login`, stores the token, gates the rest of the app.
2. Admin: user list and create-user form.
3. HR: employee list (paginated, searchable, with country and department filters).
4. HR: employee create / edit form.
5. Salary insights dashboard — three views backed by the Phase 5 endpoints (by country, by job title within a country, by department).
6. Employee documents — upload, list, download, delete per employee.

The frontend test stack (Vitest + React Testing Library) is decided at the start of this phase.

---

## Phase 8 — Polish & submission

- README final pass — architecture overview, run instructions, test instructions, and a short design-decisions section.
- Seed script that creates a default admin user, so a reviewer can log in immediately after `docker compose up`.
- Clean-clone smoke test: `docker compose up` and `pytest` from a fresh checkout, end-to-end.
- Final tag.

---

## Out of scope (and why)

Captured here so the final README's "What I'd build next" section can speak to it credibly, and so the absence of these features in the codebase is a deliberate choice rather than an oversight.

- **Attendance / leave module** — check-in/out, daily records, leave balance, accrual policies. A whole sub-system that the brief does not ask for; deferring it keeps the assessment tightly scoped to what was asked.
- **Cloud file storage** for documents (S3 etc.) — the local bind-mount keeps the assessment self-contained and reviewable from a clean clone, without external credentials.
- **Audit-log table** beyond the `created_by_id` reference and the timestamp columns that every model carries.

---

## Open questions

These were deliberately left open until the phase that needed them, so the decision was made with the most context.

- **Employee deletion** — soft- or hard-delete? *Resolved in Phase 4D as soft-delete: preserves audit trail, plays nicely with salary insights that may want to see historical headcount, and the `is_active` column already existed.*
- **Department modelling** — free-form string or normalised table? *Resolved in Phase 4C as a normalised `departments` table with a case-insensitive unique index, swapped in via a data-safe migration.*
- **Role boundaries** — strict HR-only for employee endpoints, or admin-as-superuser? *Resolved as admin-as-superuser: admin can do everything HR can, matching the way real HR tools behave.*
- **Frontend testing** — Vitest + React Testing Library is the leading candidate; confirm at the start of Phase 7.
