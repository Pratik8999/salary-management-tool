from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class SalaryByCountry(BaseModel):
    country: str
    count: int
    min: Decimal
    max: Decimal
    avg: Decimal


class SalaryByJobTitle(BaseModel):
    job_title: str
    count: int
    avg: Decimal


class SalaryByDepartment(BaseModel):
    department: str
    count: int
    avg: Decimal


class TenureByDepartment(BaseModel):
    department: str
    employee_count: int
    avg_tenure_years: float


class Anniversary(BaseModel):
    employee_id: int
    full_name: str
    email: str
    department: str
    date_joined: date
    anniversary_date: date
    years: int
