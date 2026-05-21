from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_hr
from app.db.session import get_db
from app.departments.service import get_or_create_department
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

    data = payload.model_dump()
    department = get_or_create_department(db, data.pop("department"))
    employee = Employee(
        **data, department_id=department.id, created_by_id=hr.id
    )
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
        filters.append(func.lower(Department.name) == department.lower())
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


@router.get("/departments", response_model=list[str])
def list_departments(
    db: Session = Depends(get_db),
    _hr: User = Depends(get_current_hr),
) -> list[str]:
    rows = db.execute(
        select(Department.name)
        .join(Employee, Employee.department_id == Department.id)
        .where(Employee.is_active.is_(True))
        .distinct()
        .order_by(Department.name)
    ).scalars().all()
    return list(rows)


@router.get("/{employee_id}", response_model=EmployeeRead)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    _hr: User = Depends(get_current_hr),
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
    _hr: User = Depends(get_current_hr),
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

    if "department" in updates:
        dept = get_or_create_department(db, updates.pop("department"))
        employee.department_id = dept.id

    for field, value in updates.items():
        setattr(employee, field, value)

    db.flush()
    db.refresh(employee)
    return employee
