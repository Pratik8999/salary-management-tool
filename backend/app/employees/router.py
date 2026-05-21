from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_hr
from app.db.session import get_db
from app.employees.schemas import EmployeeCreate, EmployeePage, EmployeeRead
from app.models.employee import Employee
from app.models.user import User

router = APIRouter(prefix="/api/employees", tags=["employees"])


@router.post("", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
    hr: User = Depends(get_current_hr),
) -> Employee:
    existing = db.execute(
        select(Employee).where(Employee.email == payload.email)
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already exists"
        )

    employee = Employee(**payload.model_dump(), created_by_id=hr.id)
    db.add(employee)
    db.flush()
    db.refresh(employee)
    return employee


@router.get("", response_model=EmployeePage)
def list_employees(
    q: str | None = Query(default=None, min_length=1, max_length=100),
    department: str | None = Query(default=None, min_length=1, max_length=100),
    include_inactive: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _hr: User = Depends(get_current_hr),
) -> EmployeePage:
    filters = []
    if not include_inactive:
        filters.append(Employee.is_active.is_(True))
    if department is not None:
        filters.append(Employee.department == department)
    if q is not None:
        pattern = f"%{q}%"
        filters.append(
            or_(
                Employee.first_name.ilike(pattern),
                Employee.last_name.ilike(pattern),
                Employee.email.ilike(pattern),
                Employee.job_title.ilike(pattern),
            )
        )

    base_stmt = select(Employee).where(*filters)
    total = db.execute(
        select(func.count()).select_from(base_stmt.subquery())
    ).scalar_one()
    items = (
        db.execute(base_stmt.order_by(Employee.id).limit(limit).offset(offset))
        .scalars()
        .all()
    )
    return EmployeePage(items=list(items), total=total, limit=limit, offset=offset)


@router.get("/departments", response_model=list[str])
def list_departments(
    db: Session = Depends(get_db),
    _hr: User = Depends(get_current_hr),
) -> list[str]:
    rows = db.execute(
        select(Employee.department)
        .where(Employee.is_active.is_(True))
        .distinct()
        .order_by(Employee.department)
    ).scalars().all()
    return list(rows)
