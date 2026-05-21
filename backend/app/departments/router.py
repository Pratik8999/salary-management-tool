from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_current_hr_or_admin
from app.db.session import get_db
from app.departments.schemas import (
    DepartmentCreate,
    DepartmentRead,
)
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


@router.post(
    "", response_model=DepartmentRead, status_code=status.HTTP_201_CREATED
)
def create_department(
    payload: DepartmentCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> Department:
    existing = db.execute(
        select(Department).where(func.lower(Department.name) == payload.name.lower())
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A department with that name already exists",
        )

    dept = Department(name=payload.name)
    db.add(dept)
    db.flush()
    db.refresh(dept)
    return dept
