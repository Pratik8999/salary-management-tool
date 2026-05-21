from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_hr_or_admin
from app.db.session import get_db
from app.employees.schemas import (
    EmployeeCreate,
    EmployeePage,
    EmployeeRead,
    EmployeeUpdate,
)
from app.models.department import Department
from app.models.employee import Employee
from app.models.user import User

router = APIRouter(prefix="/api/employees", tags=["employees"])


def _resolve_department(db: Session, department_id: int) -> Department:
    dept = db.get(Department, department_id)
    if dept is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Department not found",
        )
    if not dept.is_active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Department is inactive",
        )
    return dept


@router.post("", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_hr_or_admin),
) -> Employee:
    existing = db.execute(
        select(Employee).where(Employee.email == payload.email)
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already exists"
        )

    _resolve_department(db, payload.department_id)
    data = payload.model_dump()
    employee = Employee(**data, created_by_id=actor.id)
    db.add(employee)
    db.flush()
    db.refresh(employee)
    return employee


@router.get("", response_model=EmployeePage)
def list_employees(
    q: str | None = Query(default=None, min_length=1, max_length=100),
    department: str | None = Query(default=None, min_length=1, max_length=100),
    country: str | None = Query(default=None, min_length=1, max_length=100),
    include_inactive: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _hr: User = Depends(get_current_hr_or_admin),
) -> EmployeePage:
    filters = []
    if not include_inactive:
        filters.append(Employee.is_active.is_(True))
    if department is not None:
        filters.append(func.lower(Department.name) == department.lower())
    if country is not None:
        filters.append(func.lower(Employee.country) == country.lower())
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

    base_stmt = select(Employee).join(Department, Employee.department_id == Department.id).where(*filters)
    total = db.execute(
        select(func.count()).select_from(base_stmt.subquery())
    ).scalar_one()
    items = (
        db.execute(base_stmt.order_by(Employee.id).limit(limit).offset(offset))
        .scalars()
        .all()
    )
    return EmployeePage(items=list(items), total=total, limit=limit, offset=offset)


@router.get("/{employee_id}", response_model=EmployeeRead)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    _hr: User = Depends(get_current_hr_or_admin),
) -> Employee:
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found"
        )
    return employee


@router.patch("/{employee_id}", response_model=EmployeeRead)
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
    _hr: User = Depends(get_current_hr_or_admin),
) -> Employee:
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found"
        )

    updates = payload.model_dump(exclude_unset=True)

    new_email = updates.get("email")
    if new_email is not None and new_email != employee.email:
        clash = db.execute(
            select(Employee).where(Employee.email == new_email)
        ).scalar_one_or_none()
        if clash is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already exists",
            )

    if "department_id" in updates:
        _resolve_department(db, updates["department_id"])

    for field, value in updates.items():
        setattr(employee, field, value)

    db.flush()
    db.refresh(employee)
    return employee


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    _hr: User = Depends(get_current_hr_or_admin),
) -> Response:
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found"
        )
    employee.is_active = False
    db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
