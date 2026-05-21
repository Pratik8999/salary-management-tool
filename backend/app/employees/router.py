from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_hr
from app.db.session import get_db
from app.employees.schemas import EmployeeCreate, EmployeeRead
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
