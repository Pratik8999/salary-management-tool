from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_hr_or_admin
from app.db.session import get_db
from app.insights.schemas import (
    SalaryByCountry,
    SalaryByDepartment,
    SalaryByJobTitle,
)
from app.models.department import Department
from app.models.employee import Employee
from app.models.user import User

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
