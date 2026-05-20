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
- Tests cover any model-level invariants: unique employee code, joining-date sanity, computed full name. Pure columns are not tested directly.
- Model and migration follow.

### 4B · Employee CRUD
One endpoint per slice, test-first.

- `POST /employees`
- `GET /employees` — paginated and searchable. The brief mentions ~10,000 employees, so the list endpoint is designed with that scale in mind from the start (server-side pagination, indexed search columns).
- `GET /employees/{id}`
- `PATCH /employees/{id}`
- `DELETE /employees/{id}` — hard- vs soft-delete is decided at the start of this iteration; see the open questions section.

**Exit criteria.** HR users can perform a full CRUD lifecycle on employees via the API, with pagination and search verified by tests.

---

## Phase 5 — Salary / compensation domain

Depends on Employee. The exact shape of the salary structure (flat fields vs. a normalised components table, history vs. snapshots) is locked at the start of this phase based on the agreed feature list.

- Salary model and migration. Any computed fields (e.g. CTC as the sum of components) are built test-first.
- Endpoints for assigning and updating salary.
- Salary history endpoint.

Sub-iterations are refined when this phase opens.

---

## Phase 6 — Leave / attendance domain

Depends on Employee. Follows the same pattern: model first, then endpoints, with any business rules (accrual, balance, carry-forward) test-driven.

Sub-iterations are refined when this phase opens.

---

## Phase 7 — Frontend slices

Frontend work begins once the backend API contract is stable. Each screen is built as its own slice, with a component test where the screen has non-trivial logic.

1. Login screen — calls `/auth/login`, stores the token, gates the rest of the app.
2. Admin: user list and create-user form.
3. HR: employee list (paginated, searchable).
4. HR: employee create / edit form.
5. Salary screens.
6. Leave screens.

The frontend test stack (Vitest + React Testing Library) is decided at the start of this phase.

---

## Phase 8 — Polish & submission

- README final pass — architecture overview, run instructions, test instructions, and a short design-decisions section.
- Seed script that creates a default admin user, so a reviewer can log in immediately after `docker compose up`.
- Clean-clone smoke test: `docker compose up` and `pytest` from a fresh checkout, end-to-end.
- Final tag.

---

## Open questions

These are deliberately left open until the phase that needs them, so the decision is made with the most context.

- **Employee deletion** — soft-delete (preserve audit trail, simpler with salary/leave history) or hard-delete (simpler model)? Revisit at the start of Phase 4B.
- **Salary shape** — flat fields on the employee record, or a normalised components table with history? Revisit at the start of Phase 5.
- **Leave policy** — accrual rules hard-coded for now, or configurable per company from day one? Revisit at the start of Phase 6.
- **Frontend testing** — Vitest + React Testing Library is the leading candidate; confirm at the start of Phase 7.
