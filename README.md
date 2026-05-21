# Salary Management Tool

A salary management application for HR, designed for ~10,000 employees with rich analytics and insights. Built with a TDD-first workflow.

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
├── backend/    # FastAPI service
├── frontend/   # React + Vite + Tailwind UI
├── plan/       # Development plan (phases, ordering, open questions)
└── README.md
```

## Run with Docker (recommended)

The whole stack — backend, frontend, and database — comes up with one command.

```bash
cp .env.example .env
docker compose up --build
```

Then open:

- Frontend → <http://localhost:5173>
- Backend health → <http://localhost:8000/api/health>
- Postgres → `localhost:5432` (credentials from `.env`)

To stop and remove containers (keeping the database volume):

```bash
docker compose down
```

## Run Locally (without Docker)

### Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

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

If no `admin@example.com` user exists, one is created with password `admin123`
so the script is usable on a fresh clone. The seed is idempotent — running it
twice replaces the first batch rather than piling on.

Typical timings on the dev stack: **~2.8s for 10,000 rows** (single
transaction, 1,000-row INSERT batches).
