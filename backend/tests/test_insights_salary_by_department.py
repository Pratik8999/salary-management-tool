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
    email: str,
    department: str,
    salary: Decimal | int,
    is_active: bool = True,
) -> Employee:
    dept = get_or_create_department(db_session, department)
    employee = Employee(
        first_name="Test",
        last_name="Person",
        email=email,
        job_title="Software Engineer",
        country="UK",
        salary=salary,
        department_id=dept.id,
        employment_type=EmploymentType.FULL_TIME,
        date_joined=date(2024, 1, 15),
        is_active=is_active,
        created_by_id=hr.id,
    )
    db_session.add(employee)
    db_session.flush()
    db_session.refresh(employee)
    return employee


@pytest.mark.asyncio
async def test_returns_headcount_and_avg_per_department(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(
        db_session, hr, email="e1@example.com",
        department="Engineering", salary=50000,
    )
    _make_employee(
        db_session, hr, email="e2@example.com",
        department="Engineering", salary=70000,
    )
    _make_employee(
        db_session, hr, email="s1@example.com",
        department="Sales", salary=40000,
    )

    response = await client.get(
        "/api/insights/salary/by-department", headers=_auth(hr)
    )

    assert response.status_code == 200
    body = response.json()
    by_dept = {row["department"]: row for row in body}

    assert set(by_dept.keys()) == {"Engineering", "Sales"}

    eng = by_dept["Engineering"]
    assert eng["count"] == 2
    assert Decimal(eng["avg"]) == Decimal("60000")

    sales = by_dept["Sales"]
    assert sales["count"] == 1
    assert Decimal(sales["avg"]) == Decimal("40000")


@pytest.mark.asyncio
async def test_excludes_inactive_employees(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(
        db_session, hr, email="active@example.com",
        department="Engineering", salary=50000,
    )
    _make_employee(
        db_session, hr, email="inactive@example.com",
        department="Engineering", salary=99999, is_active=False,
    )

    response = await client.get(
        "/api/insights/salary/by-department", headers=_auth(hr)
    )

    body = response.json()
    assert len(body) == 1
    assert body[0]["count"] == 1
    assert Decimal(body[0]["avg"]) == Decimal("50000")


@pytest.mark.asyncio
async def test_results_ordered_by_department_name(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(
        db_session, hr, email="e1@example.com", department="Sales", salary=1
    )
    _make_employee(
        db_session, hr, email="e2@example.com", department="Engineering", salary=1
    )
    _make_employee(
        db_session, hr, email="e3@example.com", department="HR", salary=1
    )

    response = await client.get(
        "/api/insights/salary/by-department", headers=_auth(hr)
    )

    departments = [row["department"] for row in response.json()]
    assert departments == ["Engineering", "HR", "Sales"]


@pytest.mark.asyncio
async def test_returns_empty_when_no_active_employees(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)

    response = await client.get(
        "/api/insights/salary/by-department", headers=_auth(hr)
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_unauthenticated_returns_401(client):
    response = await client.get("/api/insights/salary/by-department")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_can_access(client, db_session):
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)
    response = await client.get(
        "/api/insights/salary/by-department", headers=_auth(admin)
    )
    assert response.status_code == 200
