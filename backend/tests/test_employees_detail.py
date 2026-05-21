from datetime import date
from decimal import Decimal

import pytest

from app.auth.jwt_handler import create_access_token
from app.departments.service import get_or_create_department
from app.models.employee import Employee, EmploymentType
from app.models.user import User, UserRole


def _seeded_user(db_session, *, email: str, role: UserRole) -> User:
    user = User(email=email, role=role)
    user.set_password("any-password")
    db_session.add(user)
    db_session.flush()
    db_session.refresh(user)
    return user


def _auth(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def _make_employee(
    db_session,
    hr: User,
    *,
    first_name: str = "Ada",
    last_name: str = "Lovelace",
    email: str = "ada@example.com",
    job_title: str = "Software Engineer",
    country: str = "UK",
    department: str = "Engineering",
    salary: Decimal | int = 50000,
    employment_type: EmploymentType = EmploymentType.FULL_TIME,
    date_joined: date = date(2024, 1, 15),
    is_active: bool = True,
) -> Employee:
    dept = get_or_create_department(db_session, department)
    employee = Employee(
        first_name=first_name,
        last_name=last_name,
        email=email,
        job_title=job_title,
        country=country,
        salary=salary,
        department_id=dept.id,
        employment_type=employment_type,
        date_joined=date_joined,
        is_active=is_active,
        created_by_id=hr.id,
    )
    db_session.add(employee)
    db_session.flush()
    db_session.refresh(employee)
    return employee


@pytest.mark.asyncio
async def test_returns_employee_detail(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)

    response = await client.get(
        f"/api/employees/{employee.id}", headers=_auth(hr)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == employee.id
    assert body["first_name"] == "Ada"
    assert body["last_name"] == "Lovelace"
    assert body["full_name"] == "Ada Lovelace"
    assert body["email"] == "ada@example.com"
    assert body["job_title"] == "Software Engineer"
    assert body["country"] == "UK"
    assert body["department"] == "Engineering"
    assert body["employment_type"] == EmploymentType.FULL_TIME.value
    assert body["date_joined"] == "2024-01-15"
    assert body["is_active"] is True
    assert body["created_by_id"] == hr.id
    assert "created_at" in body
    assert "updated_at" in body


@pytest.mark.asyncio
async def test_returns_inactive_employee_by_id(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(
        db_session, hr, email="inactive@example.com", is_active=False
    )

    response = await client.get(
        f"/api/employees/{employee.id}", headers=_auth(hr)
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False


@pytest.mark.asyncio
async def test_returns_404_when_not_found(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)

    response = await client.get("/api/employees/999999", headers=_auth(hr))

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_unauthenticated_returns_401(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)

    response = await client.get(f"/api/employees/{employee.id}")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_can_fetch_employee(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    employee = _make_employee(db_session, hr)
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)

    response = await client.get(
        f"/api/employees/{employee.id}", headers=_auth(admin)
    )

    assert response.status_code == 200
    assert response.json()["id"] == employee.id
