from fastapi import FastAPI

from app.auth.router import router as auth_router
from app.users.admin_router import router as admin_users_router

app = FastAPI(title="Salary Management API", version="0.1.0")

app.include_router(auth_router)
app.include_router(admin_users_router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
