from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_hr_or_admin
from app.db.session import get_db
from app.departments.schemas import DepartmentRead
from app.models.department import Department
from app.models.user import User, UserRole

router = APIRouter(prefix="/api/departments", tags=["departments"])


@router.get("", response_model=list[DepartmentRead])
def list_departments(
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_hr_or_admin),
) -> list[Department]:
    stmt = select(Department).order_by(Department.name)
    # Only admins can request inactive departments; HR is silently scoped
    # to the active set so the dropdown stays clean.
    if not (include_inactive and actor.role is UserRole.ADMIN):
        stmt = stmt.where(Department.is_active.is_(True))
    return list(db.execute(stmt).scalars())
