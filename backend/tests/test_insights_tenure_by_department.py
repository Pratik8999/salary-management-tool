from datetime import date, timedelta
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
    date_joined: date,
    is_active: bool = True,
) -> Employee:
    dept = get_or_create_department(db_session, department)
    emp = Employee(
        first_name="X",
        last_name="Y",
        email=email,
        job_title="Software Engineer",
        country="UK",
        salary=Decimal("50000"),
        department_id=dept.id,
        employment_type=EmploymentType.FULL_TIME,
        date_joined=date_joined,
        is_active=is_active,
        created_by_id=hr.id,
    )
    db_session.add(emp)
    db_session.flush()
    return emp


@pytest.mark.asyncio
async def test_by_department_returns_avg_tenure_and_count(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    today = date.today()
    # Two engineers: 4 years and 2 years -> avg 3.
    _make_employee(
        db_session,
        hr,
        email="e1@example.com",
        department="Engineering",
        date_joined=today - timedelta(days=365 * 4),
    )
    _make_employee(
        db_session,
        hr,
        email="e2@example.com",
        department="Engineering",
        date_joined=today - timedelta(days=365 * 2),
    )
    # One in sales, 1 year.
    _make_employee(
        db_session,
        hr,
        email="s1@example.com",
        department="Sales",
        date_joined=today - timedelta(days=365),
    )

    response = await client.get(
        "/api/insights/tenure/by-department", headers=_auth(hr)
    )

    assert response.status_code == 200
    body = response.json()
    by_name = {row["department"]: row for row in body}
    assert by_name["Engineering"]["employee_count"] == 2
    # Allow a tiny float wobble around 3.0 from leap days.
    assert abs(by_name["Engineering"]["avg_tenure_years"] - 3.0) < 0.05
    assert by_name["Sales"]["employee_count"] == 1
    assert abs(by_name["Sales"]["avg_tenure_years"] - 1.0) < 0.05


@pytest.mark.asyncio
async def test_by_department_excludes_inactive_employees(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    today = date.today()
    _make_employee(
        db_session,
        hr,
        email="a@example.com",
        department="Engineering",
        date_joined=today - timedelta(days=365 * 4),
    )
    _make_employee(
        db_session,
        hr,
        email="b@example.com",
        department="Engineering",
        date_joined=today - timedelta(days=365 * 10),
        is_active=False,
    )

    response = await client.get(
        "/api/insights/tenure/by-department", headers=_auth(hr)
    )

    assert response.status_code == 200
    by_name = {row["department"]: row for row in response.json()}
    assert by_name["Engineering"]["employee_count"] == 1
    assert abs(by_name["Engineering"]["avg_tenure_years"] - 4.0) < 0.05


@pytest.mark.asyncio
async def test_by_department_omits_departments_with_no_active_employees(
    client, db_session
):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    # Empty department exists but has nobody assigned.
    get_or_create_department(db_session, "Empty")
    _make_employee(
        db_session,
        hr,
        email="a@example.com",
        department="Engineering",
        date_joined=date.today() - timedelta(days=365),
    )

    response = await client.get(
        "/api/insights/tenure/by-department", headers=_auth(hr)
    )

    assert response.status_code == 200
    names = [r["department"] for r in response.json()]
    assert "Engineering" in names
    assert "Empty" not in names


@pytest.mark.asyncio
async def test_by_department_unauthenticated_returns_401(client):
    response = await client.get("/api/insights/tenure/by-department")
    assert response.status_code == 401
