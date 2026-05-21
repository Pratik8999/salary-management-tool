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
