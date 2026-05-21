from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.employee import EmploymentType


class EmployeeBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    job_title: str = Field(min_length=1, max_length=150)
    country: str = Field(min_length=1, max_length=100)
    salary: Decimal
    employment_type: EmploymentType
    date_joined: date

    @field_validator("salary")
    @classmethod
    def _salary_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("salary must be greater than 0")
        return v

    @field_validator("date_joined")
    @classmethod
    def _date_joined_not_in_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("date_joined cannot be in the future")
        return v


class EmployeeCreate(EmployeeBase):
    department_id: int


class EmployeeUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    job_title: str | None = Field(default=None, min_length=1, max_length=150)
    country: str | None = Field(default=None, min_length=1, max_length=100)
    salary: Decimal | None = None
    department_id: int | None = None
    employment_type: EmploymentType | None = None
    date_joined: date | None = None
    is_active: bool | None = None

    @field_validator("salary")
    @classmethod
    def _salary_must_be_positive(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v <= 0:
            raise ValueError("salary must be greater than 0")
        return v

    @field_validator("date_joined")
    @classmethod
    def _date_joined_not_in_future(cls, v: date | None) -> date | None:
        if v is not None and v > date.today():
            raise ValueError("date_joined cannot be in the future")
        return v


class EmployeeRead(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    full_name: str
    department_id: int
    department: str
    created_by_id: int
    created_at: datetime
    updated_at: datetime


class EmployeePage(BaseModel):
    items: list[EmployeeRead]
    total: int
    limit: int
    offset: int
