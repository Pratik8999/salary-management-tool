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
