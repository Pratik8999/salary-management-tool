# Backend — Salary Management API

FastAPI service for the Salary Management Tool. Managed with [`uv`](https://docs.astral.sh/uv/).

## Run locally

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

Health check: <http://localhost:8000/api/health>
