from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_hr_or_admin
from app.db.session import get_db
from app.insights.schemas import (
    Anniversary,
    SalaryByCountry,
    SalaryByDepartment,
    SalaryByJobTitle,
    TenureByDepartment,
)
from app.models.department import Department
from app.models.employee import Employee
from app.models.user import User

ANNIVERSARY_MILESTONES = (1, 3, 5, 10)

router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get("/salary/by-country", response_model=list[SalaryByCountry])
def salary_by_country(
    db: Session = Depends(get_db),
    _hr: User = Depends(get_current_hr_or_admin),
) -> list[SalaryByCountry]:
    rows = db.execute(
        select(
            Employee.country.label("country"),
            func.count().label("count"),
            func.min(Employee.salary).label("min"),
            func.max(Employee.salary).label("max"),
            func.avg(Employee.salary).label("avg"),
        )
        .where(Employee.is_active.is_(True))
        .group_by(Employee.country)
        .order_by(Employee.country)
    ).all()

    return [
        SalaryByCountry(
            country=row.country,
            count=row.count,
            min=row.min,
            max=row.max,
            avg=row.avg,
        )
        for row in rows
    ]


@router.get("/salary/by-job-title", response_model=list[SalaryByJobTitle])
def salary_by_job_title(
    country: str = Query(..., min_length=1, max_length=100),
    db: Session = Depends(get_db),
    _hr: User = Depends(get_current_hr_or_admin),
) -> list[SalaryByJobTitle]:
    rows = db.execute(
        select(
            Employee.job_title.label("job_title"),
            func.count().label("count"),
            func.avg(Employee.salary).label("avg"),
        )
        .where(
            Employee.is_active.is_(True),
            func.lower(Employee.country) == country.lower(),
        )
        .group_by(Employee.job_title)
        .order_by(Employee.job_title)
    ).all()

    return [
        SalaryByJobTitle(
            job_title=row.job_title, count=row.count, avg=row.avg
        )
        for row in rows
    ]


@router.get("/salary/by-department", response_model=list[SalaryByDepartment])
def salary_by_department(
    db: Session = Depends(get_db),
    _hr: User = Depends(get_current_hr_or_admin),
) -> list[SalaryByDepartment]:
    rows = db.execute(
        select(
            Department.name.label("department"),
            func.count().label("count"),
            func.avg(Employee.salary).label("avg"),
        )
        .join(Employee, Employee.department_id == Department.id)
        .where(Employee.is_active.is_(True))
        .group_by(Department.name)
        .order_by(Department.name)
    ).all()

    return [
        SalaryByDepartment(
            department=row.department, count=row.count, avg=row.avg
        )
        for row in rows
    ]


@router.get("/tenure/by-department", response_model=list[TenureByDepartment])
def tenure_by_department(
    db: Session = Depends(get_db),
    _hr: User = Depends(get_current_hr_or_admin),
) -> list[TenureByDepartment]:
    today = date.today()
    # 365.25 averages over the leap year cycle. Doing the math in days +
    # divide-on-the-way-out beats juggling DATE_PART('year', ...) across
    # dialects and matches what the spec asks for: "average tenure".
    days_since_join = func.extract("epoch", func.now() - Employee.date_joined) / 86400.0
    rows = db.execute(
        select(
            Department.name.label("department"),
            func.count().label("employee_count"),
            func.avg(days_since_join).label("avg_days"),
        )
        .join(Employee, Employee.department_id == Department.id)
        .where(Employee.is_active.is_(True))
        .group_by(Department.name)
        .order_by(Department.name)
    ).all()

    return [
        TenureByDepartment(
            department=row.department,
            employee_count=row.employee_count,
            avg_tenure_years=round(float(row.avg_days) / 365.25, 2),
        )
        for row in rows
        if row.employee_count > 0
    ]


def _next_anniversary(joined: date, today: date) -> tuple[date, int]:
    """Return (next_anniversary_date, completed_years_at_that_date).

    Handles the joined-on-Feb-29 edge by shifting that anniversary to
    March 1 in non-leap years, matching the convention HR systems use.
    """
    year = today.year
    try:
        candidate = joined.replace(year=year)
    except ValueError:
        # Feb 29 in a non-leap year -> March 1.
        candidate = date(year, 3, 1)
    if candidate < today:
        year += 1
        try:
            candidate = joined.replace(year=year)
        except ValueError:
            candidate = date(year, 3, 1)
    return candidate, candidate.year - joined.year


@router.get("/tenure/anniversaries", response_model=list[Anniversary])
def tenure_anniversaries(
    within_days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    _hr: User = Depends(get_current_hr_or_admin),
) -> list[Anniversary]:
    today = date.today()
    rows = db.execute(
        select(Employee, Department.name.label("department"))
        .join(Department, Department.id == Employee.department_id)
        .where(Employee.is_active.is_(True))
    ).all()

    out: list[Anniversary] = []
    for emp, department_name in rows:
        anniv, years = _next_anniversary(emp.date_joined, today)
        if years not in ANNIVERSARY_MILESTONES:
            continue
        if (anniv - today).days > within_days:
            continue
        out.append(
            Anniversary(
                employee_id=emp.id,
                full_name=f"{emp.first_name} {emp.last_name}",
                email=emp.email,
                department=department_name,
                date_joined=emp.date_joined,
                anniversary_date=anniv,
                years=years,
            )
        )

    out.sort(key=lambda a: (a.anniversary_date, a.employee_id))
    return out
