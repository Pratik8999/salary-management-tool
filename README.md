# Salary Management Tool

A salary management application for HR managers, designed to handle 10,000+ employees with rich analytics and insights. Built with a TDD-first workflow.

## Tech Stack

| Layer | Choice |
|---|---|
| Backend | Python + FastAPI (managed with [uv](https://docs.astral.sh/uv/)) |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy + Alembic |
| Testing | pytest + pytest-asyncio |
| Frontend | React + Vite + Tailwind CSS |
| Containerization | Docker + Docker Compose |
| Reverse Proxy | Nginx |

## Monorepo Layout

```
.
├── backend/         # FastAPI service
├── frontend/        # React + Vite + Tailwind UI
├── planning/        # HLD, schema, architecture, tradeoffs, AI prompt log
└── README.md
```

## Run Locally

### Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

Health: <http://localhost:8000/api/health>

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App: <http://localhost:5173>

## Status

Day 1: monorepo skeleton with runnable React frontend and FastAPI backend. More features added incrementally — see commit history.
