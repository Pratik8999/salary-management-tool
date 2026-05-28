# Salary Management Tool

A salary management application for HR, designed for ~10,000 employees with rich analytics and insights. Built with a TDD-first workflow.

The instance is seeded with 5,000 employees across 10 departments and 10 countries.

The high-level design (architecture, data model, trade-offs) is documented in [`plan/HLD.md`](plan/HLD.md). How AI was used during development is documented in [`plan/AI_USAGE.md`](plan/AI_USAGE.md).

## Tech Stack

| Layer | Choice |
|---|---|
| Backend | Python + FastAPI (managed with [uv](https://docs.astral.sh/uv/)) |
| Database | PostgreSQL 17 |
| ORM | SQLAlchemy + Alembic |
| Testing | pytest + pytest-asyncio |
| Frontend | React + Vite + Tailwind CSS + shadcn/ui |
| Containerization | Docker + Docker Compose |

## Monorepo Layout

```
.
├── backend/    # FastAPI service (app, alembic migrations, seed)
├── frontend/   # React + Vite + Tailwind UI
├── README.md
└── docker-compose.yml
```

## Prerequisites

- Docker + Docker Compose (for the recommended path)
- Or, for local-without-Docker: Python 3.13, [uv](https://docs.astral.sh/uv/), Node 22+, and a running Postgres 17

---

## Run with Docker (recommended)

The whole stack — backend, frontend, and database — comes up with one command.

```bash
cp .env.example .env
docker compose up --build
```

Then open:

- Frontend → <http://localhost:5173>
- Backend health → <http://localhost:8000/api/health>
- API docs (Swagger) → <http://localhost:8000/docs>
- Postgres → `localhost:5432` (credentials from `.env`)

### Useful compose commands

```bash
# Start in the background
docker compose up -d --build

# Tail logs for a single service
docker compose logs -f backend

# Restart a single service after a code change
docker compose restart backend

# Rebuild after a Dockerfile or dependency change
docker compose up -d --build backend

# Stop and remove containers (keeps the DB volume)
docker compose down

# Stop and wipe everything, including the DB volume
docker compose down -v
```

---

## Seed the Database

The seed script wipes the employee data and bulk-inserts a configurable
number of employees (default 10,000), reading first/last names from
`backend/seed/first_names.txt` and `backend/seed/last_names.txt`. Departments
are reset to a fixed catalog of 10. **Users are left alone**, so the admin
account survives across reseeds.

```bash
# Inside the running backend container (recommended):
docker compose exec backend python -m seed --count 10000 --seed 42

# Or locally, against your .env DATABASE_URL:
cd backend && uv run python -m seed --count 10000 --seed 42
```

If no `admin@example.com` user exists, one is created with password `admin123`,
and an HR user `hr@example.com` / `hr123` is created the same way — so the
script is usable on a fresh clone. The seed is idempotent — running it twice
replaces the first batch rather than piling on.

Typical timings on the dev stack: **~2.8s for 10,000 rows** (single
transaction, 1,000-row INSERT batches).

---

## Run Locally (without Docker)

### Backend

```bash
cd backend
uv sync                                       # install deps into .venv
uv run alembic upgrade head                   # apply migrations
uv run uvicorn app.main:app --reload --port 8000
```

The backend reads `DATABASE_URL` from your shell or `.env`; point it at a
running Postgres before starting.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The dev server proxies `/api/*` to <http://localhost:8000> via Vite, so the
two halves stay decoupled.

---

## Tests

### Backend (pytest)

The suite runs against a real Postgres database (`salary_management_test`)
and uses a transactional per-test fixture so tests roll back cleanly. The
`db` container must be running.

```bash
# Inside the container
docker compose exec backend uv run pytest

# Or locally — needs Postgres on localhost:5432
cd backend && uv run pytest

# A single file
cd backend && uv run pytest tests/test_employees_list.py

# A single test, with short tracebacks
cd backend && uv run pytest tests/test_employees_list.py::test_returns_paginated_envelope --tb=short

# Show print() output as it runs (handy for debugging)
cd backend && uv run pytest -s

# Stop on the first failure
cd backend && uv run pytest -x
```

### Frontend (Vitest + React Testing Library)

```bash
cd frontend

# One-shot run (CI style)
npm test -- --run

# Watch mode
npm test

# A single file
npm test -- --run src/pages/EmployeesPage.test.jsx
```

---

## Migrations (Alembic)

Migrations live at `backend/alembic/versions/` and are applied automatically
when the backend container starts, but you can drive them directly too:

```bash
# Apply everything
docker compose exec backend uv run alembic upgrade head

# Roll back one revision
docker compose exec backend uv run alembic downgrade -1

# Generate a new revision after editing a model (review the diff before committing!)
docker compose exec backend uv run alembic revision --autogenerate -m "describe change"
```

---

## Default Credentials

| Role | Email | Password |
|---|---|---|
| Admin | `admin@example.com` | `admin123` |
| HR | `hr@example.com` | `hr123` |

Both are created by the seed script only if the email is missing — pre-existing users are never touched.

Reset / create users via the admin UI at `/admin/users` once you're signed in,
or directly in Postgres if you need to recover.

---

## Deploy on a server (production stack)

The `docker-compose.prod.yml` overlay builds production images and exposes
only port 80. The frontend is built to static files and served by nginx,
which also reverse-proxies `/api` to the backend. Postgres and the backend
have no host port mappings — they only talk over the internal compose network.

```bash
# On the server, after cloning the repo:
cp .env.example .env
# edit .env — at minimum set a strong JWT_SECRET and a non-default POSTGRES_PASSWORD

docker compose -f docker-compose.prod.yml up -d --build
```

The backend container runs `alembic upgrade head` on every start, so schema
changes apply automatically. Seed data is opt-in:

```bash
docker compose -f docker-compose.prod.yml exec backend python -m seed --count 10000
```

Open `http://<server-ip>/` and log in with the credentials in the table above.

**Firewall / Security Group:** open inbound 80 (anywhere), 22 (your IP only).
Do **not** expose 5432 or 8000 publicly — the prod compose intentionally
doesn't map them.

**Updating after a code change:**

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

---

## Project Layout

```
backend/
├── app/
│   ├── auth/           # login, JWT, role guards
│   ├── departments/    # admin CRUD + dropdown source
│   ├── documents/      # employee document upload/download
│   ├── employees/      # employee CRUD + list filters/sort
│   ├── insights/       # salary + tenure + overview analytics
│   ├── users/          # admin user management
│   ├── models/         # SQLAlchemy models
│   └── db/             # session, base, mixins
├── alembic/            # migrations
├── seed/               # 10k-employee bulk seed + name lists
└── tests/              # pytest suite (one file per endpoint/feature)

frontend/
├── src/
│   ├── api/            # axios clients per resource
│   ├── components/     # shared widgets + shadcn/ui
│   ├── lib/            # auth context, api instance, utils
│   ├── pages/          # one file per screen
│   └── routes/         # AppRoutes + ProtectedRoute
└── tests live next to the file they cover (`Foo.test.jsx`)
```
