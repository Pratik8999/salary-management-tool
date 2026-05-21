import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
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
from app.models.employee import Employee, EmploymentType
from app.models.user import User

# Single source of truth for the sortable columns. Keeping it here (and not
# inferring from request strings) means an unknown sort value fails
# validation up front instead of silently falling back to "by id".
SORT_OPTIONS = {
    "salary_asc": Employee.salary.asc(),
    "salary_desc": Employee.salary.desc(),
    "date_joined_asc": Employee.date_joined.asc(),
    "date_joined_desc": Employee.date_joined.desc(),
    "name_asc": (Employee.first_name.asc(), Employee.last_name.asc()),
    "name_desc": (Employee.first_name.desc(), Employee.last_name.desc()),
}

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


def _employee_filters(
    *,
    q: str | None,
    department: str | None,
    department_id: int | None,
    country: str | None,
    job_title: str | None,
    employment_type: EmploymentType | None,
    include_inactive: bool,
) -> list:
    filters: list = []
    if not include_inactive:
        filters.append(Employee.is_active.is_(True))
    if department is not None:
        filters.append(func.lower(Department.name) == department.lower())
    if department_id is not None:
        filters.append(Employee.department_id == department_id)
    if country is not None:
        filters.append(func.lower(Employee.country) == country.lower())
    if job_title is not None:
        filters.append(Employee.job_title.ilike(f"%{job_title}%"))
    if employment_type is not None:
        filters.append(Employee.employment_type == employment_type)
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
    return filters


def _order_clauses(sort: str | None):
    if sort is None:
        return (Employee.id,)
    chosen = SORT_OPTIONS[sort]
    # Always end on Employee.id so paging through a tied sort key
    # (e.g. two employees on the same salary) stays stable.
    return (*chosen, Employee.id) if isinstance(chosen, tuple) else (chosen, Employee.id)


def _validate_sort(sort: str | None) -> None:
    if sort is not None and sort not in SORT_OPTIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unknown sort value: {sort}",
        )


@router.get("", response_model=EmployeePage)
def list_employees(
    q: str | None = Query(default=None, min_length=1, max_length=100),
    department: str | None = Query(default=None, min_length=1, max_length=100),
    department_id: int | None = Query(default=None, ge=1),
    country: str | None = Query(default=None, min_length=1, max_length=100),
    job_title: str | None = Query(default=None, min_length=1, max_length=150),
    employment_type: EmploymentType | None = Query(default=None),
    sort: str | None = Query(default=None),
    include_inactive: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _hr: User = Depends(get_current_hr_or_admin),
) -> EmployeePage:
    _validate_sort(sort)
    filters = _employee_filters(
        q=q,
        department=department,
        department_id=department_id,
        country=country,
        job_title=job_title,
        employment_type=employment_type,
        include_inactive=include_inactive,
    )

    base_stmt = (
        select(Employee)
        .join(Department, Employee.department_id == Department.id)
        .where(*filters)
    )
    total = db.execute(
        select(func.count()).select_from(base_stmt.subquery())
    ).scalar_one()

    items = (
        db.execute(
            base_stmt.order_by(*_order_clauses(sort)).limit(limit).offset(offset)
        )
        .scalars()
        .all()
    )
    return EmployeePage(items=list(items), total=total, limit=limit, offset=offset)


EXPORT_COLUMNS = [
    "id",
    "first_name",
    "last_name",
    "email",
    "job_title",
    "department",
    "country",
    "salary",
    "employment_type",
    "date_joined",
    "is_active",
]


def _row_for_csv(emp: Employee) -> list:
    return [
        emp.id,
        emp.first_name,
        emp.last_name,
        emp.email,
        emp.job_title,
        emp.department,  # property -> department_ref.name
        emp.country,
        str(emp.salary),
        emp.employment_type.value,
        emp.date_joined.isoformat(),
        str(emp.is_active).lower(),
    ]


@router.get("/export.csv")
def export_employees_csv(
    q: str | None = Query(default=None, min_length=1, max_length=100),
    department: str | None = Query(default=None, min_length=1, max_length=100),
    department_id: int | None = Query(default=None, ge=1),
    country: str | None = Query(default=None, min_length=1, max_length=100),
    job_title: str | None = Query(default=None, min_length=1, max_length=150),
    employment_type: EmploymentType | None = Query(default=None),
    sort: str | None = Query(default=None),
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    _hr: User = Depends(get_current_hr_or_admin),
) -> StreamingResponse:
    _validate_sort(sort)
    filters = _employee_filters(
        q=q,
        department=department,
        department_id=department_id,
        country=country,
        job_title=job_title,
        employment_type=employment_type,
        include_inactive=include_inactive,
    )
    stmt = (
        select(Employee)
        .join(Department, Employee.department_id == Department.id)
        .where(*filters)
        .order_by(*_order_clauses(sort))
    )

    def _stream():
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(EXPORT_COLUMNS)
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
        for emp in db.execute(stmt).scalars():
            writer.writerow(_row_for_csv(emp))
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

    filename = f"employees-{date.today().isoformat()}.csv"
    return StreamingResponse(
        _stream(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/countries", response_model=list[str])
def list_countries(
    db: Session = Depends(get_db),
    _hr: User = Depends(get_current_hr_or_admin),
) -> list[str]:
    rows = (
        db.execute(
            select(Employee.country)
            .where(Employee.is_active.is_(True))
            .distinct()
            .order_by(Employee.country)
        )
        .scalars()
        .all()
    )
    return list(rows)


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
