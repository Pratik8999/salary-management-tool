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
    country: str,
    salary: Decimal | int,
    job_title: str = "Software Engineer",
    department: str = "Engineering",
    is_active: bool = True,
) -> Employee:
    dept = get_or_create_department(db_session, department)
    employee = Employee(
        first_name="Test",
        last_name="Person",
        email=email,
        job_title=job_title,
        country=country,
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
async def test_returns_aggregates_per_country(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(db_session, hr, email="uk1@example.com", country="UK", salary=50000)
    _make_employee(db_session, hr, email="uk2@example.com", country="UK", salary=70000)
    _make_employee(db_session, hr, email="us1@example.com", country="US", salary=100000)

    response = await client.get(
        "/api/insights/salary/by-country", headers=_auth(hr)
    )

    assert response.status_code == 200
    body = response.json()
    by_country = {row["country"]: row for row in body}

    assert set(by_country.keys()) == {"UK", "US"}

    uk = by_country["UK"]
    assert uk["count"] == 2
    assert Decimal(uk["min"]) == Decimal("50000")
    assert Decimal(uk["max"]) == Decimal("70000")
    assert Decimal(uk["avg"]) == Decimal("60000")

    us = by_country["US"]
    assert us["count"] == 1
    assert Decimal(us["min"]) == Decimal("100000")
    assert Decimal(us["max"]) == Decimal("100000")
    assert Decimal(us["avg"]) == Decimal("100000")


@pytest.mark.asyncio
async def test_results_ordered_by_country_name(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(db_session, hr, email="us@example.com", country="US", salary=1)
    _make_employee(db_session, hr, email="in@example.com", country="IN", salary=1)
    _make_employee(db_session, hr, email="uk@example.com", country="UK", salary=1)

    response = await client.get(
        "/api/insights/salary/by-country", headers=_auth(hr)
    )

    assert response.status_code == 200
    countries = [row["country"] for row in response.json()]
    assert countries == ["IN", "UK", "US"]


@pytest.mark.asyncio
async def test_excludes_inactive_employees(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)
    _make_employee(
        db_session, hr, email="active@example.com", country="UK", salary=50000
    )
    _make_employee(
        db_session,
        hr,
        email="inactive@example.com",
        country="UK",
        salary=99999,
        is_active=False,
    )

    response = await client.get(
        "/api/insights/salary/by-country", headers=_auth(hr)
    )

    body = response.json()
    assert len(body) == 1
    assert body[0]["country"] == "UK"
    assert body[0]["count"] == 1
    assert Decimal(body[0]["max"]) == Decimal("50000")


@pytest.mark.asyncio
async def test_returns_empty_when_no_active_employees(client, db_session):
    hr = _seeded_user(db_session, email="hr@example.com", role=UserRole.HR)

    response = await client.get(
        "/api/insights/salary/by-country", headers=_auth(hr)
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_unauthenticated_returns_401(client):
    response = await client.get("/api/insights/salary/by-country")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_cannot_access(client, db_session):
    admin = _seeded_user(db_session, email="admin@example.com", role=UserRole.ADMIN)
    response = await client.get(
        "/api/insights/salary/by-country", headers=_auth(admin)
    )
    assert response.status_code == 403
