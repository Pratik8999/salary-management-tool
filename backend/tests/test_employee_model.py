from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.employee import Employee, EmploymentType
from app.models.user import User, UserRole


def _hr(db_session) -> User:
    user = User(email="hr@example.com", role=UserRole.HR)
    user.set_password("any-password")
    db_session.add(user)
    db_session.flush()
    db_session.refresh(user)
    return user


def _employee_kwargs(**overrides):
    base = dict(
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        job_title="Software Engineer",
        country="UK",
        salary=Decimal("50000.00"),
        department="Engineering",
        employment_type=EmploymentType.FULL_TIME,
        date_joined=date(2024, 1, 15),
    )
    base.update(overrides)
    return base


def test_full_name_concatenates_first_and_last():
    employee = Employee(**_employee_kwargs())
    assert employee.full_name == "Ada Lovelace"


def test_full_name_handles_extra_whitespace():
    employee = Employee(
        **_employee_kwargs(first_name="  Ada  ", last_name="  Lovelace  ")
    )
    assert employee.full_name == "Ada Lovelace"


def test_employment_type_enum_values():
    assert EmploymentType("full_time") is EmploymentType.FULL_TIME
    assert EmploymentType("part_time") is EmploymentType.PART_TIME
    assert EmploymentType("contract") is EmploymentType.CONTRACT


def test_employment_type_rejects_unknown_value():
    with pytest.raises(ValueError):
        EmploymentType("intern")


def test_email_is_unique(db_session):
    hr = _hr(db_session)
    db_session.add(Employee(created_by_id=hr.id, **_employee_kwargs()))
    db_session.flush()

    db_session.add(
        Employee(
            created_by_id=hr.id,
            **_employee_kwargs(first_name="Different", last_name="Person"),
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_is_active_defaults_to_true(db_session):
    hr = _hr(db_session)
    employee = Employee(created_by_id=hr.id, **_employee_kwargs())
    db_session.add(employee)
    db_session.flush()
    db_session.refresh(employee)
    assert employee.is_active is True


def test_created_by_relation_resolves_to_user(db_session):
    hr = _hr(db_session)
    employee = Employee(created_by_id=hr.id, **_employee_kwargs())
    db_session.add(employee)
    db_session.flush()
    db_session.refresh(employee)
    assert employee.created_by is not None
    assert employee.created_by.email == "hr@example.com"


def test_persists_with_all_required_fields(db_session):
    hr = _hr(db_session)
    employee = Employee(created_by_id=hr.id, **_employee_kwargs())
    db_session.add(employee)
    db_session.flush()
    db_session.refresh(employee)

    assert employee.id is not None
    assert employee.email == "ada@example.com"
    assert employee.salary == Decimal("50000.00")
    assert employee.employment_type is EmploymentType.FULL_TIME
    assert employee.date_joined == date(2024, 1, 15)
    assert employee.created_at is not None
    assert employee.updated_at is not None


def test_future_date_joined_is_rejected_by_schema():
    from app.employees.schemas import EmployeeCreate

    future = date.today() + timedelta(days=1)
    with pytest.raises(ValueError):
        EmployeeCreate(**_employee_kwargs(date_joined=future))


def test_non_positive_salary_is_rejected_by_schema():
    from app.employees.schemas import EmployeeCreate

    with pytest.raises(ValueError):
        EmployeeCreate(**_employee_kwargs(salary=Decimal("0")))

    with pytest.raises(ValueError):
        EmployeeCreate(**_employee_kwargs(salary=Decimal("-10")))
