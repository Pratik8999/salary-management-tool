from fastapi import FastAPI

from app.auth.router import router as auth_router
from app.employees.router import router as employees_router
from app.insights.router import router as insights_router
from app.users.admin_router import router as admin_users_router

app = FastAPI(title="Salary Management API", version="0.1.0")

app.include_router(auth_router)
app.include_router(admin_users_router)
app.include_router(employees_router)
app.include_router(insights_router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
